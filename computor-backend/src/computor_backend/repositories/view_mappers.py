import logging
from sqlalchemy.orm import Session, joinedload
from computor_types.course_content_types import CourseContentTypeList, CourseContentTypeGet
from computor_types.student_course_contents import (
    CourseContentStudentList,
    CourseContentStudentGet,
    ResultStudentList,
    ResultStudentGet,
    SubmissionGroupStudentList,
    SubmissionGroupStudentGet,
    SubmissionGroupRepository,
    SubmissionGroupMemberBasic,
)
from computor_types.results import ResultArtifactInfo
from computor_types.grading import GradingStatus, SubmissionGroupGradingList, GradedByCourseMember
from computor_types.tasks import map_int_to_task_status
from computor_types.deployment import CourseContentDeploymentList
from computor_backend.model.course import CourseMember
from computor_backend.model.artifact import SubmissionGrade, SubmissionArtifact
from computor_backend.repositories.course_content import CourseMemberCourseContentQueryResult
from computor_backend.services.result_storage import retrieve_result_json, list_result_artifacts

logger = logging.getLogger(__name__)

async def course_member_course_content_result_mapper(
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
    submission_group_unread_count = course_member_course_content_result.submission_group_unread_count
    latest_grade_status_int = course_member_course_content_result.latest_grade_status_int
    is_latest_unreviewed = course_member_course_content_result.is_latest_unreviewed

    submission_group_unread_count = submission_group_unread_count or 0
    # Only count submission_group messages for course content unread count
    unread_message_count = submission_group_unread_count
    
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

    # Convert latest_grade_status_int to string
    latest_grade_status = status_lookup.get(latest_grade_status_int) if latest_grade_status_int is not None else None

    # unreviewed_count: 1 if latest submission is unreviewed, 0 otherwise
    # For units, this will be aggregated later
    unreviewed_count = is_latest_unreviewed or 0

    directory = course_content.deployment.deployment_path if course_content.deployment else None

    # Build deployment information if present
    deployment_payload = None
    has_deployment = False
    if hasattr(course_content, 'deployment') and course_content.deployment:
        has_deployment = True
        deployment_payload = CourseContentDeploymentList.model_validate(
            course_content.deployment,
            from_attributes=True
        )

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

        # Fetch result_json and artifacts from MinIO only for detailed views
        if detailed:
            result_json_data = await retrieve_result_json(result.id)
            artifacts = await list_result_artifacts(result.id)
            result_artifacts = [
                ResultArtifactInfo(
                    id=f"{result.id}_{artifact['filename']}",
                    filename=artifact['filename'],
                    content_type=artifact.get('content_type'),
                    file_size=artifact['size'],
                    created_at=artifact['last_modified'].isoformat() if artifact.get('last_modified') else None,
                )
                for artifact in artifacts
            ]
            result_payload = ResultStudentGet(
                id=str(result.id),
                testing_service_id=result.testing_service_id,
                test_system_id=result.test_system_id,
                version_identifier=result.version_identifier,
                status=map_int_to_task_status(result.status),
                result=result.result,
                result_json=result_json_data,
                submit=submit_value,
                result_artifacts=result_artifacts,
            )
        else:
            # For list views, don't fetch result_json from MinIO
            result_payload = ResultStudentList(
                id=str(result.id),
                testing_service_id=result.testing_service_id,
                test_system_id=result.test_system_id,
                version_identifier=result.version_identifier,
                status=map_int_to_task_status(result.status),
                result=result.result,
                submit=submit_value,
            )

    # Query grades directly from database for this submission group
    gradings_payload = []
    latest_submission_artifact_id = None
    if submission_group is not None:
        # First, find the latest submission artifact (submit=true) ordered by created_at
        latest_submission = db.query(SubmissionArtifact).filter(
            SubmissionArtifact.submission_group_id == submission_group.id,
            SubmissionArtifact.submit == True
        ).order_by(SubmissionArtifact.created_at.desc()).first()

        if latest_submission:
            latest_submission_artifact_id = latest_submission.id

        # Get all grades for this submission group (for the gradings list)
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

    # Update latest grading values from the latest SUBMISSION's most recent grade
    # (not just the most recent grade overall)
    graded_by_course_member_payload = None
    if latest_submission_artifact_id is not None:
        # Find the latest grade for the latest submission artifact
        latest_submission_grade = db.query(SubmissionGrade).filter(
            SubmissionGrade.artifact_id == latest_submission_artifact_id
        ).options(
            joinedload(SubmissionGrade.graded_by).joinedload(CourseMember.user),
            joinedload(SubmissionGrade.graded_by).joinedload(CourseMember.course_role),
        ).order_by(SubmissionGrade.graded_at.desc()).first()

        if latest_submission_grade:
            latest_grading_value = latest_submission_grade.grade
            latest_status_value = latest_submission_grade.status
            # Get the grader info from the latest grading
            if latest_submission_grade.graded_by:
                graded_by_course_member_payload = GradedByCourseMember.model_validate(
                    latest_submission_grade.graded_by, from_attributes=True
                )

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
            graded_by_course_member=graded_by_course_member_payload,
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
            graded_by_course_member=graded_by_course_member_payload,
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
        testing_service_id=str(course_content.testing_service_id) if course_content.testing_service_id else None,
        directory=directory,
        color=course_content.course_content_type.color,
        result=result_payload,
        submission_group=submission_group_payload,
        unread_message_count=unread_message_count,
        deployment=deployment_payload,
        has_deployment=has_deployment,
        # Status: for submittable contents, use submission_group.status
        # For units, this will be aggregated later by the view repository
        status=submission_status,
        # Whether latest submission is unreviewed (for units, this is aggregated)
        unreviewed_count=unreviewed_count,
        # Latest grade status of the latest submission artifact
        latest_grade_status=latest_grade_status,
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
        course_content_type=CourseContentTypeGet.model_validate(course_content.course_content_type),
        result_count=list_obj.result_count,
        submission_count=list_obj.submission_count,
        max_test_runs=list_obj.max_test_runs,
        testing_service_id=list_obj.testing_service_id,
        unread_message_count=list_obj.unread_message_count,
        result=list_obj.result,
        directory=list_obj.directory,
        color=list_obj.color,
        submission_group=submission_group_detail or (
            SubmissionGroupStudentGet(**submission_group_payload.model_dump())
            if submission_group_payload is not None else None
        ),
        deployment=deployment_payload,
        has_deployment=has_deployment,
        status=list_obj.status,
        unreviewed_count=list_obj.unreviewed_count,
        latest_grade_status=list_obj.latest_grade_status,
    )
