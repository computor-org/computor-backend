import logging
from sqlalchemy.orm import Session, joinedload
from computor_types.course_content_types import CourseContentTypeList, CourseContentTypeGet
from computor_types.student_course_contents import (
    CourseContentStudentList,
    CourseContentStudentGet,
    ResultStudentList,
    SubmissionGroupStudentList,
    SubmissionGroupStudentGet,
    SubmissionGroupRepository,
    SubmissionGroupMemberBasic,
)
from computor_types.grading import GradingStatus, SubmissionGroupGradingList, GradedByCourseMember
from computor_types.tasks import map_int_to_task_status
from computor_backend.model.course import CourseMember
from computor_backend.model.artifact import SubmissionGrade, SubmissionArtifact
from computor_backend.repositories.course_content import CourseMemberCourseContentQueryResult

logger = logging.getLogger(__name__)

def course_member_course_content_result_mapper(
    course_member_course_content_result: CourseMemberCourseContentQueryResult,
    db: Session = None,
    detailed: bool = False
):
    """
    Map CourseMemberCourseContentQueryResult to CourseContentStudent DTOs.

    Args:
        course_member_course_content_result: Typed query result from repository
        db: Database session (required for fetching grades)
        detailed: Whether to return detailed (Get) or list (List) DTO

    Returns:
        CourseContentStudentList or CourseContentStudentGet
    """
    # Use typed model fields instead of tuple unpacking
    course_content = course_member_course_content_result.course_content
    result_count = course_member_course_content_result.result_count
    result = course_member_course_content_result.result
    submission_group = course_member_course_content_result.submission_group
    submission_count = course_member_course_content_result.submission_count
    submission_status_int = course_member_course_content_result.submission_status_int
    submission_grading = course_member_course_content_result.submission_grading
    content_unread_count = course_member_course_content_result.content_unread_count
    submission_group_unread_count = course_member_course_content_result.submission_group_unread_count

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

    directory = course_content.deployment.deployment_path if course_content.deployment else None

    repository = None
    if submission_group != None and submission_group.properties != None:
        gitlab_info = submission_group.properties.get('gitlab', {})
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
        # Get submit field from associated SubmissionArtifact
        submit_value = False
        if result.submission_artifact:
            submit_value = result.submission_artifact.submit

        result_payload = ResultStudentList(
            execution_backend_id=result.execution_backend_id,
            test_system_id=result.test_system_id,
            version_identifier=result.version_identifier,
            status=map_int_to_task_status(result.status),
            result=result.result,
            result_json=result.result_json,
            submit=submit_value,
        )

    # Query grades directly from database for this submission group
    gradings_payload = []
    if submission_group is not None:
        grades = db.query(SubmissionGrade).join(
            SubmissionArtifact, SubmissionArtifact.id == SubmissionGrade.artifact_id
        ).filter(
            SubmissionArtifact.submission_group_id == submission_group.id
        ).options(
            joinedload(SubmissionGrade.graded_by).joinedload(CourseMember.user),
            joinedload(SubmissionGrade.graded_by).joinedload(CourseMember.course_role),
        ).order_by(SubmissionGrade.graded_at.desc()).all()

        for grade in grades:
            gradings_payload.append(SubmissionGroupGradingList(
                id=str(grade.id),
                submission_group_id=str(submission_group.id),
                graded_by_course_member_id=str(grade.graded_by_course_member_id),
                result_id=None,
                grading=grade.grade,
                status=GradingStatus(grade.status),
                feedback=grade.comment,
                created_at=grade.created_at,
                graded_by_course_member=GradedByCourseMember.model_validate(grade.graded_by, from_attributes=True) if grade.graded_by else None,
            ))

    # # Update latest grading values from most recent grade
    if gradings_payload:
        latest_grading_value = gradings_payload[0].grading
        latest_status = gradings_payload[0].status
        latest_status_value = latest_status.value if isinstance(latest_status, GradingStatus) else latest_status

    if latest_status_value is not None:
        submission_status = status_lookup.get(int(latest_status_value), "not_reviewed")

    submission_grading = latest_grading_value

    submission_group_payload = None
    submission_group_detail = None
    if submission_group is not None:
        members = [
            SubmissionGroupMemberBasic(
                id=str(member.id),
                user_id=str(member.course_member.user_id),
                course_member_id=str(member.course_member_id),
                username=member.course_member.user.username if member.course_member.user else None,
                full_name=f"{member.course_member.user.given_name} {member.course_member.user.family_name}".strip() if member.course_member.user else None,
            )
            for member in submission_group.members
        ]

        submission_group_payload = SubmissionGroupStudentList(
            id=str(submission_group.id),
            course_content_title=None,
            course_content_path=None,
            example_identifier=None,
            max_group_size=submission_group.max_group_size,
            current_group_size=len(submission_group.members),
            members=members,
            repository=repository,
            status=submission_status,
            grading=submission_grading,
            count=submission_count or 0,
            max_submissions=submission_group.max_submissions,
            unread_message_count=submission_group_unread_count,
        )

        submission_group_detail = SubmissionGroupStudentGet(
            id=str(submission_group.id),
            course_content_title=None,
            course_content_path=None,
            example_identifier=None,
            max_group_size=submission_group.max_group_size,
            current_group_size=len(submission_group.members),
            members=members,
            repository=repository,
            status=submission_status,
            grading=submission_grading,
            count=submission_count or 0,
            max_submissions=submission_group.max_submissions,
            unread_message_count=submission_group_unread_count,
            gradings=gradings_payload,
        )

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
