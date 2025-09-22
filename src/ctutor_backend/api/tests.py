from typing import Annotated
import logging
from fastapi import Depends, APIRouter
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ctutor_backend.api.exceptions import BadRequestException, InternalServerException, NotFoundException
from ctutor_backend.permissions.auth import get_current_permissions
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.api.results import get_result_status
from ctutor_backend.database import get_db
from ctutor_backend.interface.course_contents import CourseContentGet
from ctutor_backend.interface.courses import CourseProperties
from ctutor_backend.interface.organizations import OrganizationProperties
from ctutor_backend.interface.repositories import Repository
from ctutor_backend.interface.results import ResultCreate
from ctutor_backend.interface.tasks import TaskStatus, map_int_to_task_status, map_task_status_to_int
from ctutor_backend.interface.tests import TestCreate, TestJob
from ctutor_backend.interface.tokens import decrypt_api_key
from ctutor_backend.model.auth import User
from ctutor_backend.model.course import Course, CourseContent, CourseContentType, CourseExecutionBackend, CourseMember, CourseSubmissionGroup, CourseSubmissionGroupMember, CourseFamily
from ctutor_backend.model.organization import Organization
from ctutor_backend.model.result import Result
from ctutor_backend.model.execution import ExecutionBackend
from ctutor_backend.model.example import Example, ExampleVersion
from ctutor_backend.model.deployment import CourseContentDeployment
from ..custom_types import Ltree
from ctutor_backend.tasks import get_task_executor, TaskSubmission
class TestRunResponse(ResultCreate):
    id: str

def build_test_run_response(result: Result) -> TestRunResponse:
    """Convert a Result ORM instance into the API response model."""
    return TestRunResponse(
        id=str(result.id),
        submit=result.submit,
        course_member_id=str(result.course_member_id),
        course_content_id=str(result.course_content_id),
        course_submission_group_id=str(result.course_submission_group_id) if result.course_submission_group_id else None,
        execution_backend_id=str(result.execution_backend_id),
        test_system_id=result.test_system_id,
        result=result.result,
        result_json=result.result_json,
        properties=result.properties,
        status=map_int_to_task_status(result.status),
        version_identifier=result.version_identifier,
        reference_version_identifier=result.reference_version_identifier,
    )

tests_router = APIRouter()

@tests_router.post("", response_model=TestRunResponse)
async def create_test(
    test_create: TestCreate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db)
):
    """
    Create and execute a test for a course assignment.
    Tests are now executed via Temporal workflows.
    Submit flag is stored as a boolean in the Result model.
    """
    user_id = permissions.user_id

    # Get course member
    # if test_create.provider_url == None or test_create.project == None:
    #     course_member = db.query(CourseMember).join(User, User.id == CourseMember.user_id).filter(User.id == user_id).first()
    # else:
    #     course_member = check_course_permissions(permissions, CourseMember, "_student", db) \
    #         .filter(
    #             CourseMember.properties["gitlab"].op("->>")("url") == test_create.provider_url,
    #             CourseMember.properties["gitlab"].op("->>")("full_path") == test_create.project
    #         ).first()

    course_member = db.query(CourseMember) \
        .join(User, User.id == CourseMember.user_id) \
            .join(CourseContent, CourseContent.course_id == CourseMember.course_id) \
                .filter(User.id == user_id).first()

    if not course_member:
        raise NotFoundException(detail="Course member not found")

    course_member_id = course_member.id

    # Subquery for counting existing results
    results_count_subquery = (
        db.query(
            Result.course_content_id,
            func.count(Result.id).label("total_results_count")
        )
        .group_by(Result.course_content_id)
        .subquery()
    )

    # Build main query joining necessary tables
    joined_query = db.query(
        CourseContent,
        Course,
        Organization,
        CourseSubmissionGroup.max_submissions,
        results_count_subquery.c.total_results_count,
        Example
    ) \
        .join(CourseContentType, CourseContentType.id == CourseContent.course_content_type_id) \
        .join(Course, Course.id == CourseContent.course_id) \
        .join(CourseMember, CourseMember.course_id == Course.id) \
        .join(CourseFamily, CourseFamily.id == Course.course_family_id) \
        .join(Organization, Organization.id == CourseFamily.organization_id) \
        .join(CourseExecutionBackend, CourseExecutionBackend.course_id == CourseContent.course_id) \
        .join(CourseSubmissionGroupMember, CourseSubmissionGroupMember.course_member_id == CourseMember.id) \
        .join(CourseSubmissionGroup, CourseSubmissionGroup.id == CourseSubmissionGroupMember.course_submission_group_id) \
        .outerjoin(CourseContentDeployment, CourseContentDeployment.course_content_id == CourseContent.id) \
        .outerjoin(ExampleVersion, ExampleVersion.id == CourseContentDeployment.example_version_id) \
        .outerjoin(Example, Example.id == ExampleVersion.example_id) \
        .outerjoin(
            results_count_subquery,
            (CourseContent.id == results_count_subquery.c.course_content_id)
        ).filter(Course.id == course_member.course_id, CourseMember.id == course_member_id)

    # Find the course content based on provided parameters
    if test_create.course_content_id != None:
        query_result = joined_query.filter(
            CourseContent.id == test_create.course_content_id,
            CourseContentType.course_content_kind_id == "assignment"
        ).first()
    elif test_create.course_content_path != None:
        query_result = joined_query.filter(
            CourseContent.path == Ltree(test_create.course_content_path),
            CourseContentType.course_content_kind_id == "assignment"
        ).first()
    elif test_create.directory != None:
        # Use the Example.directory field for lookup
        query_result = joined_query.filter(
            Example.directory == test_create.directory,
            CourseContentType.course_content_kind_id == "assignment"
        ).first()
    else:
        raise BadRequestException(detail="Must provide course_content_id, course_content_path, or directory")

    if not query_result:
        raise NotFoundException(detail="Assignment not found")

    # Extract query results
    course_content = query_result[0]
    course = query_result[1]
    organization = query_result[2]
    allowed_max_submissions = query_result[3]
    submissions = query_result[4] if query_result[4] != None else 0
    example = query_result[5]

    # Check max submissions limit
    if allowed_max_submissions is not None and submissions >= allowed_max_submissions:
        raise BadRequestException(detail="Reached max submissions for this course_content")

    # Convert to CourseContentGet
    try:
        assignment = CourseContentGet(**course_content.__dict__)
    except:
        raise BadRequestException(detail="Failed to process assignment")

    # Get properties
    organization_properties = OrganizationProperties(**organization.properties)
    course_properties = CourseProperties(**course.properties)
    assignment_properties = assignment.properties
    execution_backend_id = assignment.execution_backend_id

    # Validate version identifier (commit)
    commit = test_create.version_identifier
    if commit == None:
        raise BadRequestException(detail="version_identifier is required")

    # Check for existing results with same commit
    # With the new partial indexes, we can have multiple failed results with the same version_identifier
    existing_results = db.query(Result) \
        .filter(
            Result.course_member_id == course_member_id,
            Result.course_content_id == assignment.id,
            Result.version_identifier == commit
        ).all()

    # Get submission group
    course_submission_group = db.query(CourseSubmissionGroup) \
        .join(CourseSubmissionGroupMember, CourseSubmissionGroup.id == CourseSubmissionGroupMember.course_submission_group_id) \
        .filter(
            CourseSubmissionGroupMember.course_member_id == course_member_id,
            CourseSubmissionGroup.course_content_id == assignment.id
        ).first()
    
    if not course_submission_group:
        raise BadRequestException(detail="No submission group found for this assignment")
    
    course_submission_group_id = course_submission_group.id
    submission_group_properties = course_submission_group.properties or {}

    # Handle existing results
    if existing_results:
        # Sort by created_at to get the most recent
        latest_result = sorted(existing_results, key=lambda r: r.created_at, reverse=True)[0]
        
        # Check if the latest result is still running according to DB
        # Status values: 0=COMPLETED, 1=FAILED, 2=CANCELLED, 3=SCHEDULED, 4=PENDING, 5=RUNNING, 7=PAUSED
        if latest_result.status in [4, 3, 5, 7]:  # PENDING, SCHEDULED, RUNNING, PAUSED
            # Check actual Temporal workflow status
            try:
                if not latest_result.test_system_id:
                    logger.warning(
                        "Result %s is missing a test_system_id while marked as in-progress; flagging as failed",
                        latest_result.id,
                    )
                    latest_result.status = map_task_status_to_int(TaskStatus.FAILED)
                    db.commit()
                    db.refresh(latest_result)
                    # Will create a new run below
                else:
                    task_executor = get_task_executor()
                    actual_status = await task_executor.get_task_status(latest_result.test_system_id)

                    # Check Temporal status
                    if actual_status.status in [TaskStatus.QUEUED, TaskStatus.STARTED]:
                        # Still running, return the existing one
                        return build_test_run_response(latest_result)
                    elif actual_status.status == TaskStatus.FINISHED:
                        # Workflow finished, check actual task result for errors
                        actual_result = await task_executor.get_task_result(latest_result.test_system_id)

                        try:
                            actual_result_status = TaskStatus(actual_result.status)
                        except ValueError:
                            actual_result_status = TaskStatus.FAILED

                        if actual_result_status == TaskStatus.FINISHED and not actual_result.error:
                            latest_result.status = map_task_status_to_int(TaskStatus.FINISHED)
                            db.commit()
                            db.refresh(latest_result)

                            if test_create.submit and not latest_result.submit:
                                latest_result.submit = True
                                db.commit()
                                db.refresh(latest_result)
                            return build_test_run_response(latest_result)

                        # Workflow reported an error or finished unsuccessfully
                        latest_result.status = map_task_status_to_int(TaskStatus.FAILED)
                        db.commit()
                        db.refresh(latest_result)
                        # Will create a new run below
                    else:  # FAILED, CANCELLED, etc.
                        # Update DB status to failed
                        latest_result.status = map_task_status_to_int(TaskStatus.FAILED)
                        db.commit()
                        db.refresh(latest_result)
                        # Will create a new run below
            except Exception as e:
                # If we can't check Temporal (workflow doesn't exist, etc.), assume it crashed
                logger.warning(f"Could not check Temporal workflow status for {latest_result.test_system_id}: {e}")
                latest_result.status = map_task_status_to_int(TaskStatus.FAILED)
                db.commit()
                db.refresh(latest_result)
                # Will create a new run below
        
        # If completed successfully and only updating submit flag
        elif latest_result.status == 0:  # COMPLETED
            if test_create.submit and not latest_result.submit:
                latest_result.submit = True
                db.commit()
                db.refresh(latest_result)
            return build_test_run_response(latest_result)
        
        # If failed/crashed/cancelled, we'll create a new run below

    # Create new test execution
    # Build repository configurations for GitLab
    gitlab_config = submission_group_properties.get('gitlab')
    if not gitlab_config:
        raise BadRequestException(
            detail="Student repository not configured for this assignment. Please ensure student repository has been created."
        )
    
    # Validate organization GitLab configuration
    if not organization_properties.gitlab or not organization_properties.gitlab.url:
        raise BadRequestException(detail="Organization GitLab configuration is missing")
    
    # Validate course GitLab configuration
    if not course_properties.gitlab or not course_properties.gitlab.full_path:
        raise BadRequestException(detail="Course GitLab configuration is missing")

    # Get execution backend
    execution_backend = db.query(ExecutionBackend) \
        .filter(ExecutionBackend.id == execution_backend_id).first()

    if not execution_backend:
        raise BadRequestException(detail=f"Execution backend not found")

    if gitlab_config != None:
        provider = organization_properties.gitlab.url
        full_path_course = course_properties.gitlab.full_path
        
        # Resolve deployment info (directory and reference commit)
        deployment = db.query(CourseContentDeployment).filter(
            CourseContentDeployment.course_content_id == assignment.id
        ).first()
        if not deployment or not deployment.deployment_path or not deployment.version_identifier:
            raise BadRequestException(detail="Assignment not released: missing deployment path or version identifier")
        assignment_directory = deployment.deployment_path
        reference_commit = deployment.version_identifier
        
        token = decrypt_api_key(organization_properties.gitlab.token)
        
        # Validate that submission group has GitLab repository set up
        if not gitlab_config.get('full_path'):
            raise BadRequestException(
                detail="Student repository path not configured. Please ensure student repository has been created."
            )
        
        full_path_module = gitlab_config['full_path']
        full_path_reference = f"{full_path_course}/assignments"

        gitlab_path_module = f"{provider}/{full_path_module}.git"
        gitlab_path_reference = f"{provider}/{full_path_reference}.git"

        student_repository = Repository(
            url=gitlab_path_module,
            path=assignment_directory,
            token=token,
            commit=commit
        )
        reference_repository = Repository(
            url=gitlab_path_reference,
            path=assignment_directory,
            token=token,
            commit=reference_commit
        )

        job = TestJob(
            user_id=user_id,
            course_member_id=str(course_member_id),
            course_content_id=str(assignment.id),
            execution_backend_id=str(execution_backend_id),
            execution_backend_type=execution_backend.type,
            module=student_repository,
            reference=reference_repository
        )
    else:
        raise BadRequestException(detail="Only GitLab is currently supported")

    # Generate a unique workflow ID that will be used for both database and Temporal
    import uuid
    workflow_id = f"student-testing-{str(uuid.uuid4())}"

    # Create result entry with the pre-generated workflow ID
    result_create = Result(
        submit=test_create.submit or False,  # Store submit flag as boolean
        course_member_id=course_member_id,
        course_submission_group_id=course_submission_group_id,
        course_content_id=assignment.id,
        course_content_type_id=course_content.course_content_type_id,  # Keep for now, can be removed later
        execution_backend_id=execution_backend.id,
        test_system_id=workflow_id,  # Use the pre-generated workflow ID
        result=0,
        result_json=None,
        properties=None,
        status=map_task_status_to_int(TaskStatus.QUEUED),  # Start as QUEUED
        version_identifier=commit,
        reference_version_identifier=reference_commit
    )

    db.add(result_create)
    db.commit()
    db.refresh(result_create)

    # Start Temporal workflow for testing with our pre-generated workflow ID
    try:
        if str(execution_backend.type).startswith("temporal:"):
            # Use task executor to submit the task
            task_executor = get_task_executor()
            
            task_submission = TaskSubmission(
                task_name="student_testing",
                workflow_id=workflow_id,  # Use our pre-generated workflow ID
                parameters={
                    "test_job": job.model_dump(),
                    "execution_backend_properties": execution_backend.properties,
                    "result_id": str(result_create.id)  # Pass the result ID to the workflow
                },
                queue=execution_backend.properties.get("task_queue", "computor-tasks")
            )
            
            submitted_id = await task_executor.submit_task(task_submission)
            
            # Verify the workflow ID matches (should be the same)
            if submitted_id != workflow_id:
                logger.warning(f"Submitted workflow ID {submitted_id} doesn't match pre-generated ID {workflow_id}")
            
            # Update status to QUEUED now that task is submitted
            result_create.status = map_task_status_to_int(TaskStatus.QUEUED)
            db.commit()
            db.refresh(result_create)
        else:
            raise BadRequestException(f"Execution backend type '{execution_backend.type}' not supported. Use 'temporal'.")
    except Exception as e:
        # If task submission fails, update result status to FAILED
        result_create.status = map_task_status_to_int(TaskStatus.FAILED)
        result_create.properties = {"error": str(e)}
        db.commit()
        db.refresh(result_create)
        raise

    return build_test_run_response(result_create)
