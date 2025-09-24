import logging
from sqlalchemy.orm import Session, joinedload
from ctutor_backend.interface.course_content_types import CourseContentTypeList, CourseContentTypeGet
from ctutor_backend.interface.student_course_contents import (
    CourseContentStudentList,
    CourseContentStudentGet,
    ResultStudentList,
    SubmissionGroupStudentList,
    SubmissionGroupStudentGet,
    SubmissionGroupRepository,
    SubmissionGroupMemberBasic,
)
from ctutor_backend.interface.grading import GradingStatus, CourseSubmissionGroupGradingList
from ctutor_backend.interface.tasks import map_int_to_task_status
from ctutor_backend.model.course import CourseSubmissionGroupMember, CourseMember, CourseContent, CourseSubmissionGroupGrading
from ctutor_backend.model.auth import User
from ctutor_backend.model.deployment import CourseContentDeployment
from ctutor_backend.model.example import ExampleVersion, Example

logger = logging.getLogger(__name__)

def course_member_course_content_result_mapper(course_member_course_content_result, db: Session = None, detailed: bool = False):

    query = course_member_course_content_result

    course_content = query[0]
    result_count = query[1]
    result = query[2]
    course_submission_group = query[3]
    submission_count = query[4] if len(query) > 4 else None
    submission_status_int = query[5] if len(query) > 5 else None
    submission_grading = query[6] if len(query) > 6 else None
    content_unread_count = query[7] if len(query) > 7 else 0
    submission_group_unread_count = query[8] if len(query) > 8 else 0

    content_unread_count = content_unread_count or 0
    submission_group_unread_count = submission_group_unread_count or 0
    unread_message_count = content_unread_count + submission_group_unread_count
    
    # Convert integer status to string for backward compatibility
    status_lookup = {
        GradingStatus.NOT_REVIEWED.value: "not_reviewed",
        GradingStatus.CORRECTED.value: "corrected",
        GradingStatus.CORRECTION_NECESSARY.value: "correction_necessary",
        GradingStatus.IMPROVEMENT_POSSIBLE.value: "improvement_possible",
    }

    submission_status = None
    latest_status_value = submission_status_int
    latest_grading_value = submission_grading

    # Get directory from deployment's example if available, otherwise from properties
    directory = None
    if hasattr(course_content, 'deployment') and course_content.deployment and db:
        # Get the example through deployment
        from ctutor_backend.model.deployment import CourseContentDeployment
        from ctutor_backend.model.example import Example, ExampleVersion
        
        deployment = course_content.deployment

        directory = deployment.deployment_path
        # if deployment.example_version_id:
        #     # Get example version and then example
        #     example_version = db.query(ExampleVersion).filter(
        #         ExampleVersion.id == deployment.example_version_id
        #     ).first()
        #     if example_version and example_version.example:
        #         directory = example_version.example.directory
    
    # Fallback to properties if no example directory found
    # if not directory:
    #     props = course_content.properties or {}
    #     directory = props.get("gitlab", {}).get("directory")

    repository = None
    if course_submission_group != None and course_submission_group.properties != None:
        gitlab_info = course_submission_group.properties.get('gitlab', {})
        base_url = gitlab_info.get('url', '').rstrip('/')
        full_path = gitlab_info.get('full_path', '')
        clone_url = f"{base_url}/{full_path}.git"

        repository = SubmissionGroupRepository(
                            provider="gitlab",
                            url=gitlab_info.get('url', ''),
                            full_path=gitlab_info.get('full_path', ''),
                            clone_url=clone_url,
                            web_url=gitlab_info.get('web_url'))
    
    result_payload = None
    if result is not None and result.test_system_id is not None:
        result_payload = ResultStudentList(
            execution_backend_id=result.execution_backend_id,
            test_system_id=result.test_system_id,
            version_identifier=result.version_identifier,
            status=map_int_to_task_status(result.status),
            result=result.result,
            result_json=result.result_json,
            submit=result.submit,
        )

    gradings_payload = []
    if course_submission_group is not None and getattr(course_submission_group, 'gradings', None):
        sorted_gradings = sorted(
            course_submission_group.gradings,
            key=lambda g: g.created_at,
            reverse=True,
        )
        for grading in sorted_gradings:
            gradings_payload.append(CourseSubmissionGroupGradingList.model_validate(grading))

        if gradings_payload:
            latest_grading_value = gradings_payload[0].grading
            latest_status = gradings_payload[0].status
            if isinstance(latest_status, GradingStatus):
                latest_status_value = latest_status.value
            elif latest_status is not None:
                try:
                    latest_status_value = int(latest_status)
                except (TypeError, ValueError):
                    pass

    if latest_status_value is not None:
        submission_status = status_lookup.get(int(latest_status_value), "not_reviewed")

    submission_grading = latest_grading_value

    submission_group_payload = None
    submission_group_detail = None
    if course_submission_group is not None:
        submission_group_base = dict(
            id=str(course_submission_group.id),
            course_content_title=None,
            course_content_path=None,
            example_identifier=None,
            max_group_size=course_submission_group.max_group_size,
            current_group_size=len(course_submission_group.members) if getattr(course_submission_group, 'members', None) else 1,
            members=[
                SubmissionGroupMemberBasic(
                    id=str(member.id),
                    user_id=member.course_member.user_id if member.course_member else '',
                    course_member_id=str(member.course_member_id),
                    username=member.course_member.user.username if member.course_member and member.course_member.user else None,
                    full_name=(
                        f"{member.course_member.user.given_name} {member.course_member.user.family_name}".strip()
                        if member.course_member and member.course_member.user
                        else None
                    ),
                )
                for member in getattr(course_submission_group, 'members', [])
            ],
            repository=repository,
            status=submission_status,
            grading=submission_grading,
            count=submission_count if submission_count is not None else 0,
            max_submissions=course_submission_group.max_submissions,
            unread_message_count=submission_group_unread_count,
        )

        submission_group_payload = SubmissionGroupStudentList(**submission_group_base)

        if gradings_payload:
            submission_group_detail = SubmissionGroupStudentGet(**submission_group_base, gradings=gradings_payload)
        else:
            submission_group_detail = SubmissionGroupStudentGet(**submission_group_base)

    list_obj = CourseContentStudentList(
        id=course_content.id,
        title=course_content.title,
        path=course_content.path,
        course_id=course_content.course_id,
        course_content_type_id=course_content.course_content_type_id,
        course_content_kind_id=course_content.course_content_kind_id,
        position=course_content.position,
        max_group_size=course_content.max_group_size,
        submitted=True if submission_count not in (None, 0) else False,
        course_content_type=CourseContentTypeList.model_validate(course_content.course_content_type),
        result_count=result_count if result_count is not None else 0,
        submission_count=submission_count if submission_count is not None else 0,
        max_test_runs=course_content.max_test_runs,
        directory=directory,
        color=course_content.course_content_type.color,
        result=result_payload,
        submission_group=submission_group_payload,
        unread_message_count=unread_message_count,
    )

    if not detailed:
        return list_obj

    return CourseContentStudentGet(
        created_at=course_content.created_at,
        updated_at=course_content.updated_at,
        id=list_obj.id,
        archived_at=course_content.archived_at,
        title=list_obj.title,
        description=course_content.description,
        path=list_obj.path,
        course_id=list_obj.course_id,
        course_content_type_id=list_obj.course_content_type_id,
        course_content_kind_id=list_obj.course_content_kind_id,
        position=list_obj.position,
        max_group_size=list_obj.max_group_size,
        submitted=list_obj.submitted,
        course_content_types=CourseContentTypeGet.model_validate(course_content.course_content_type),
        result_count=list_obj.result_count,
        submission_count=list_obj.submission_count,
        max_test_runs=list_obj.max_test_runs,
        unread_message_count=list_obj.unread_message_count,
        result=list_obj.result,
        directory=list_obj.directory,
        color=list_obj.color,
        submission_group=submission_group_detail or (
            SubmissionGroupStudentGet(**submission_group_payload.model_dump())
            if submission_group_payload is not None else None
        ),
    )
