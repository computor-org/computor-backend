"""
Refactored tests API using the new artifact/test result pattern.
This module handles test execution for submission artifacts.
"""
from typing import Annotated, Optional
import logging
import uuid
from fastapi import Depends, APIRouter
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from ctutor_backend.api.exceptions import BadRequestException, NotFoundException, ForbiddenException
from ctutor_backend.permissions.auth import get_current_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.database import get_db
from ctutor_backend.interface.results import ResultCreate, ResultList
from ctutor_backend.interface.repositories import Repository
from ctutor_backend.interface.tasks import TaskStatus, map_task_status_to_int
from ctutor_backend.interface.tests import TestCreate, TestJob
from ctutor_backend.interface.tokens import decrypt_api_key
from ctutor_backend.interface.courses import CourseProperties
from ctutor_backend.interface.organizations import OrganizationProperties
from ctutor_backend.model.artifact import SubmissionArtifact
from ctutor_backend.model.result import Result
from ctutor_backend.model.course import (
    Course, CourseContent, CourseContentType, CourseExecutionBackend,
    CourseMember, SubmissionGroup, SubmissionGroupMember, CourseFamily
)
from ctutor_backend.model.organization import Organization
from ctutor_backend.model.execution import ExecutionBackend
from ctutor_backend.model.deployment import CourseContentDeployment
from ctutor_backend.model.example import Example, ExampleVersion
from ctutor_backend.custom_types import Ltree
from ctutor_backend.tasks import get_task_executor, TaskSubmission
from ctutor_backend.interface.tasks import map_int_to_task_status

logger = logging.getLogger(__name__)

tests_router = APIRouter()


@tests_router.post("", response_model=ResultList)
async def create_test_run(
    test_create: TestCreate,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db)
):
    """
    Create and execute a test for a submission artifact.

    Ways to specify what to test:
    1. Provide artifact_id directly
    2. Provide submission_group_id + version_identifier to find specific version
    3. Provide submission_group_id only to test the latest submission

    Tests are executed via Temporal workflows.
    """
    user_id = permissions.get_user_id()

    # Determine which artifact to test
    artifact = None

    if test_create.artifact_id:
        # Direct artifact ID provided
        artifact = db.query(SubmissionArtifact).filter(
            SubmissionArtifact.id == test_create.artifact_id
        ).first()

        if not artifact:
            raise NotFoundException(detail="Submission artifact not found")

    elif test_create.submission_group_id:
        # Find artifact by submission group and optional version
        if test_create.version_identifier:
            # Find specific version
            artifact = db.query(SubmissionArtifact).filter(
                SubmissionArtifact.submission_group_id == test_create.submission_group_id,
                SubmissionArtifact.version_identifier == test_create.version_identifier
            ).order_by(SubmissionArtifact.created_at.desc()).first()

            if not artifact:
                raise NotFoundException(
                    detail=f"No artifact found for submission group {test_create.submission_group_id} "
                           f"with version {test_create.version_identifier}"
                )
        else:
            # Get latest submission for the group
            artifact = db.query(SubmissionArtifact).filter(
                SubmissionArtifact.submission_group_id == test_create.submission_group_id
            ).order_by(SubmissionArtifact.created_at.desc()).first()

            if not artifact:
                raise NotFoundException(
                    detail=f"No artifacts found for submission group {test_create.submission_group_id}. "
                           f"Student must submit first."
                )
    else:
        raise BadRequestException(
            detail="Must provide either artifact_id or submission_group_id to identify what to test"
        )

    # Get the submission group with permission check
    submission_group = check_course_permissions(
        permissions, SubmissionGroup, "_student", db
    ).filter(
        SubmissionGroup.id == artifact.submission_group_id
    ).first()

    if not submission_group:
        raise NotFoundException(detail="Submission group not found or access denied")

    # Get course member who is running the test
    course_member = db.query(CourseMember).filter(
        CourseMember.user_id == user_id,
        CourseMember.course_id == submission_group.course_id
    ).first()

    if not course_member:
        raise NotFoundException(detail="You are not a member of this course")

    # Check for existing test results for this artifact by this member
    # Apply test limitation: prevent multiple successful tests
    existing_test = db.query(Result).filter(
        and_(
            Result.submission_artifact_id == artifact.id,
            Result.course_member_id == course_member.id,
            ~Result.status.in_([1, 2, 6])  # Not failed, cancelled, or crashed
        )
    ).first()

    if existing_test:
        # Check if still running
        if existing_test.status in [3, 4, 5, 7]:  # SCHEDULED, PENDING, RUNNING, PAUSED
            # Check actual Temporal workflow status if available
            if existing_test.test_system_id:
                try:
                    task_executor = get_task_executor()
                    actual_status = await task_executor.get_task_status(existing_test.test_system_id)

                    if actual_status.status in [TaskStatus.QUEUED, TaskStatus.STARTED]:
                        # Still running, return the existing one
                        return ResultList.model_validate(existing_test)
                except Exception as e:
                    logger.warning(f"Could not check Temporal status: {e}")

        # If completed successfully, don't allow another test
        elif existing_test.status == 0:  # COMPLETED/FINISHED
            raise BadRequestException(
                detail="You have already successfully tested this artifact. "
                       "Multiple tests are not allowed unless the previous test failed."
            )

    # Check max test runs limit for the submission group
    if submission_group.max_test_runs is not None:
        test_count = db.query(func.count(Result.id)).filter(
            Result.submission_artifact_id == artifact.id
        ).scalar()

        if test_count >= submission_group.max_test_runs:
            raise BadRequestException(
                detail=f"Maximum test runs ({submission_group.max_test_runs}) reached for this artifact"
            )

    # Get course content (assignment)
    course_content = db.query(CourseContent).filter(
        CourseContent.id == submission_group.course_content_id
    ).first()

    if not course_content or not course_content.execution_backend_id:
        raise BadRequestException(detail="Assignment or execution backend not configured")

    # Get execution backend
    execution_backend = db.query(ExecutionBackend).filter(
        ExecutionBackend.id == course_content.execution_backend_id
    ).first()

    if not execution_backend:
        raise BadRequestException(detail="Execution backend not found")

    # Get course and organization for GitLab configuration
    course = db.query(Course).filter(Course.id == submission_group.course_id).first()
    course_family = db.query(CourseFamily).filter(CourseFamily.id == course.course_family_id).first()
    organization = db.query(Organization).filter(Organization.id == course_family.organization_id).first()

    organization_properties = OrganizationProperties(**organization.properties)
    course_properties = CourseProperties(**course.properties)

    # Get deployment info for reference repository
    deployment = db.query(CourseContentDeployment).filter(
        CourseContentDeployment.course_content_id == course_content.id
    ).first()

    if not deployment or not deployment.deployment_path or not deployment.version_identifier:
        raise BadRequestException(detail="Assignment not released: missing deployment information")

    # Build repository configurations
    submission_group_properties = submission_group.properties or {}
    gitlab_config = submission_group_properties.get('gitlab')

    if not gitlab_config or not gitlab_config.get('full_path'):
        raise BadRequestException(
            detail="Student repository not configured. Please ensure repository has been created."
        )

    # Use version identifier from artifact column, test request, or properties fallback
    artifact_properties = artifact.properties or {}
    version_identifier = (
        test_create.version_identifier or
        artifact.version_identifier or  # Use the proper column first
        artifact_properties.get('commit')  # Fallback for legacy data
    )

    if not version_identifier:
        raise BadRequestException(detail="Version identifier (commit) is required")

    # Build GitLab repository configurations
    provider = organization_properties.gitlab.url
    token = decrypt_api_key(organization_properties.gitlab.token)

    student_repository = Repository(
        url=f"{provider}/{gitlab_config['full_path']}.git",
        path=deployment.deployment_path,
        token=token,
        commit=version_identifier
    )

    reference_repository = Repository(
        url=f"{provider}/{course_properties.gitlab.full_path}/assignments.git",
        path=deployment.deployment_path,
        token=token,
        commit=deployment.version_identifier
    )

    # Create test job
    job = TestJob(
        user_id=str(user_id),
        course_member_id=str(course_member.id),
        course_content_id=str(course_content.id),
        execution_backend_id=str(execution_backend.id),
        execution_backend_type=execution_backend.type,
        module=student_repository,
        reference=reference_repository
    )

    # Generate workflow ID
    workflow_id = f"student-testing-{str(uuid.uuid4())}"

    # Create test result record
    result = Result(
        submission_artifact_id=artifact.id,
        course_member_id=course_member.id,
        execution_backend_id=execution_backend.id,
        test_system_id=workflow_id,
        status=map_task_status_to_int(TaskStatus.QUEUED),
        grade=0.0,
        result_json=None,
        properties={
            "submission_group_id": str(submission_group.id),
            "course_content_id": str(course_content.id),
            "artifact_id": str(artifact.id),  # Store artifact ID instead of non-existent filename
        },
        log_text=None,
        version_identifier=version_identifier,
        reference_version_identifier=deployment.version_identifier,
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    # Start Temporal workflow for testing
    try:
        if str(execution_backend.type).startswith("temporal:"):
            task_executor = get_task_executor()

            task_submission = TaskSubmission(
                task_name="student_testing",
                workflow_id=workflow_id,
                parameters={
                    "test_job": job.model_dump(),
                    "execution_backend_properties": execution_backend.properties,
                    "result_id": str(result.id),
                    "artifact_id": str(artifact.id),
                },
                queue=execution_backend.properties.get("task_queue", "computor-tasks")
            )

            submitted_id = await task_executor.submit_task(task_submission)

            if submitted_id != workflow_id:
                logger.warning(f"Submitted workflow ID {submitted_id} doesn't match pre-generated ID {workflow_id}")
        else:
            raise BadRequestException(f"Execution backend type '{execution_backend.type}' not supported")

    except Exception as e:
        # If task submission fails, update result status to FAILED
        result.status = map_task_status_to_int(TaskStatus.FAILED)
        result.properties = {**result.properties, "error": str(e)}
        db.commit()
        db.refresh(result)
        raise

    return ResultList.model_validate(result)


@tests_router.get("/status/{result_id}")
async def get_test_status(
    result_id: str,
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    db: Session = Depends(get_db)
):
    """Get the current status of a test execution.

    Permission rules:
    - Students can view their own test results (member of submission group)
    - Tutors and higher roles can view all test results in their courses
    """

    # Query only the fields we need, including join to get submission group for permissions
    result_data = db.query(
        Result.id,
        Result.status,
        Result.started_at,
        Result.test_system_id,
        Result.submission_artifact_id,
        SubmissionGroup.id.label("submission_group_id"),
        SubmissionGroup.course_id
    ).join(
        SubmissionArtifact, SubmissionArtifact.id == Result.submission_artifact_id
    ).join(
        SubmissionGroup, SubmissionGroup.id == SubmissionArtifact.submission_group_id
    ).filter(
        Result.id == result_id
    ).first()

    if not result_data:
        raise NotFoundException(detail="Test result not found")

    # Check permissions
    user_id = permissions.get_user_id()
    if user_id and not permissions.is_admin:
        # Check if user is a member of the submission group (for students)
        is_group_member = db.query(SubmissionGroupMember).join(
            CourseMember
        ).filter(
            SubmissionGroupMember.submission_group_id == result_data.submission_group_id,
            CourseMember.user_id == user_id
        ).first()

        if not is_group_member:
            # Not a group member, check for tutor or higher permissions
            has_elevated_perms = check_course_permissions(
                permissions, CourseMember, "_tutor", db
            ).filter(
                CourseMember.course_id == result_data.course_id,
                CourseMember.user_id == user_id
            ).first()

            if not has_elevated_perms:
                raise ForbiddenException(detail="You don't have permission to view this test result")

    # If test has a workflow ID, check Temporal status for running tests
    status = result_data.status
    if result_data.test_system_id and status in [3, 4, 5, 7]:  # Running statuses
        try:
            task_executor = get_task_executor()
            actual_status = await task_executor.get_task_status(result_data.test_system_id)

            # Update database if status changed
            new_status = map_task_status_to_int(actual_status.status)
            if new_status != status:
                # Update only the status field
                db.query(Result).filter(Result.id == result_id).update({"status": new_status})
                db.commit()
                status = new_status
        except Exception as e:
            logger.warning(f"Could not check Temporal status: {e}")

    return {
        "id": str(result_data.id),
        "status": map_int_to_task_status(status),
        "started_at": result_data.started_at,
    }