"""Result-to-DTO mappers for student/tutor course-content views.

Used by ``StudentViewRepository`` and ``TutorViewRepository`` (and the
tutor business-logic layer) to take a ``CourseMemberCourseContentQueryResult``
and produce either a list-shaped or detail-shaped student DTO. The
detail variant additionally pulls ``result_json`` and the artifact
listing from MinIO; the list variant skips that I/O.
"""
import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload

from computor_types.course_content_types import CourseContentTypeList, CourseContentTypeGet
from computor_types.deployment import CourseContentDeploymentList
from computor_types.grading import GradingStatus, SubmissionGroupGradingList, GradedByCourseMember
from computor_types.results import ResultArtifactInfo
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
from computor_types.tasks import map_int_to_task_status
from computor_backend.model.artifact import SubmissionGrade, SubmissionArtifact
from computor_backend.model.course import CourseMember
from computor_backend.repositories.course_content import CourseMemberCourseContentQueryResult
from computor_backend.services.result_storage import retrieve_result_json, list_result_artifacts

logger = logging.getLogger(__name__)


# Stored as ints in ``SubmissionGrade.status``; the student-facing DTO
# carries the string form. Module-level so the dict isn't rebuilt on
# every call. Adding a new GradingStatus member requires extending here.
_GRADING_STATUS_LOOKUP = {
    GradingStatus.NOT_REVIEWED.value: "not_reviewed",
    GradingStatus.CORRECTED.value: "corrected",
    GradingStatus.CORRECTION_NECESSARY.value: "correction_necessary",
    GradingStatus.IMPROVEMENT_POSSIBLE.value: "improvement_possible",
}


def _build_repository(submission_group) -> Optional[SubmissionGroupRepository]:
    """Materialise the GitLab repository handle from ``submission_group.properties``.

    Returns None when the group has no GitLab metadata (e.g. local dev,
    repo not yet provisioned).
    """
    if submission_group is None or submission_group.properties is None:
        return None
    gitlab_info = submission_group.properties.get('gitlab', {})
    base_url = gitlab_info.get('url', '').rstrip('/')
    full_path = gitlab_info.get('full_path', '')
    return SubmissionGroupRepository(
        provider="gitlab",
        url=gitlab_info.get('url', ''),
        full_path=full_path,
        clone_url=f"{base_url}/{full_path}.git",
        web_url=gitlab_info.get('web_url'),
    )


async def _build_result_payload(result, detailed: bool):
    """Convert a ``Result`` row to its student DTO.

    For ``detailed=True`` we additionally fetch ``result_json`` and the
    artifact listing from MinIO — the only I/O outside the database
    that this module performs.
    """
    if result is None or result.test_system_id is None:
        return None

    submit_value = result.submission_artifact.submit if result.submission_artifact else False
    common = dict(
        id=str(result.id),
        testing_service_id=result.testing_service_id,
        test_system_id=result.test_system_id,
        version_identifier=result.version_identifier,
        status=map_int_to_task_status(result.status),
        result=result.result,
        submit=submit_value,
    )

    if not detailed:
        return ResultStudentList(**common)

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
    return ResultStudentGet(
        **common,
        result_json=result_json_data,
        result_artifacts=result_artifacts,
    )


def _fetch_grades_and_latest_artifact(
    submission_group, db: Session,
) -> Tuple[List[SubmissionGroupGradingList], Optional[object]]:
    """Return ``(gradings_list, latest_submission_artifact_id)`` for a group.

    The "latest submission artifact" is the most recent artifact with
    ``submit=True``; the listing's headline grade attaches to it (see
    ``_fetch_latest_grade_for_artifact``).
    """
    if submission_group is None:
        return [], None

    latest_submission = (
        db.query(SubmissionArtifact)
        .filter(
            SubmissionArtifact.submission_group_id == submission_group.id,
            SubmissionArtifact.submit == True,  # noqa: E712 — SQLAlchemy column comparison
        )
        .order_by(SubmissionArtifact.created_at.desc())
        .first()
    )

    grades = (
        db.query(SubmissionGrade)
        .join(SubmissionArtifact, SubmissionArtifact.id == SubmissionGrade.artifact_id)
        .filter(SubmissionArtifact.submission_group_id == submission_group.id)
        .options(
            joinedload(SubmissionGrade.graded_by).joinedload(CourseMember.user),
            joinedload(SubmissionGrade.graded_by).joinedload(CourseMember.course_role),
        )
        .order_by(SubmissionGrade.graded_at.desc())
        .all()
    )

    gradings = [
        SubmissionGroupGradingList(
            id=str(grade.id),
            submission_group_id=str(submission_group.id),
            graded_by_course_member_id=str(grade.graded_by_course_member_id),
            result_id=None,
            grading=grade.grade,
            status=GradingStatus(grade.status),
            feedback=grade.comment,
            created_at=grade.created_at,
            graded_by_course_member=(
                GradedByCourseMember.model_validate(grade.graded_by, from_attributes=True)
                if grade.graded_by else None
            ),
        )
        for grade in grades
    ]
    return gradings, (latest_submission.id if latest_submission else None)


def _fetch_latest_grade_for_artifact(artifact_id, db: Session) -> Optional[SubmissionGrade]:
    """Most-recent ``SubmissionGrade`` row for ``artifact_id`` (or None)."""
    if artifact_id is None:
        return None
    return (
        db.query(SubmissionGrade)
        .filter(SubmissionGrade.artifact_id == artifact_id)
        .options(
            joinedload(SubmissionGrade.graded_by).joinedload(CourseMember.user),
            joinedload(SubmissionGrade.graded_by).joinedload(CourseMember.course_role),
        )
        .order_by(SubmissionGrade.graded_at.desc())
        .first()
    )


def _build_submission_group_payloads(
    submission_group,
    *,
    repository: Optional[SubmissionGroupRepository],
    submission_status: Optional[str],
    submission_grading,
    submission_count: int,
    unread: int,
    graded_by_course_member_payload: Optional[GradedByCourseMember],
    gradings_payload: List[SubmissionGroupGradingList],
    detailed: bool,
) -> Tuple[Optional[SubmissionGroupStudentList], Optional[SubmissionGroupStudentGet]]:
    """Build the list and (optionally) detail submission-group DTOs.

    Detail is only built when ``detailed=True`` — the previous
    implementation built both unconditionally and discarded one,
    paying a Pydantic validation cost for nothing.
    """
    if submission_group is None:
        return None, None

    members = [
        SubmissionGroupMemberBasic(
            id=str(member.id),
            user_id=str(member.course_member.user_id),
            course_member_id=str(member.course_member_id),
            username=member.course_member.user.username if member.course_member.user else None,
            full_name=(
                f"{member.course_member.user.given_name} {member.course_member.user.family_name}".strip()
                if member.course_member.user else None
            ),
        )
        for member in submission_group.members
    ]

    common = dict(
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
        count=submission_count,
        max_submissions=submission_group.max_submissions,
        unread_message_count=unread,
        graded_by_course_member=graded_by_course_member_payload,
    )

    list_payload = SubmissionGroupStudentList(**common)
    detail_payload = (
        SubmissionGroupStudentGet(**common, gradings=gradings_payload)
        if detailed else None
    )
    return list_payload, detail_payload


async def course_member_course_content_result_mapper(
    course_member_course_content_result: CourseMemberCourseContentQueryResult,
    db: Session,
    detailed: bool = False,
):
    """Map a query result to a CourseContentStudent DTO.

    ``detailed=True`` returns ``CourseContentStudentGet`` (richer, hits
    MinIO for ``result_json``/artifact listing); ``detailed=False``
    returns the lighter ``CourseContentStudentList`` and stays in the
    database.
    """
    qr = course_member_course_content_result
    course_content = qr.course_content
    submission_group = qr.submission_group

    unread = qr.submission_group_unread_count or 0

    deployment = course_content.deployment
    deployment_payload = (
        CourseContentDeploymentList.model_validate(deployment, from_attributes=True)
        if deployment else None
    )
    has_deployment = deployment is not None
    directory = deployment.deployment_path if deployment else None

    repository = _build_repository(submission_group)
    result_payload = await _build_result_payload(qr.result, detailed)

    gradings_payload, latest_artifact_id = _fetch_grades_and_latest_artifact(submission_group, db)

    # The headline grade in the listing follows the *latest submitted artifact*,
    # not just the most-recent grade overall — students should see the verdict
    # on what they actually submitted, not on a prior attempt.
    latest_grade = _fetch_latest_grade_for_artifact(latest_artifact_id, db)
    if latest_grade is not None:
        latest_grading_value = latest_grade.grade
        latest_status_value = latest_grade.status
        graded_by_course_member_payload = (
            GradedByCourseMember.model_validate(latest_grade.graded_by, from_attributes=True)
            if latest_grade.graded_by else None
        )
    else:
        latest_grading_value = qr.submission_grading
        latest_status_value = qr.submission_status_int
        graded_by_course_member_payload = None

    submission_status = (
        _GRADING_STATUS_LOOKUP.get(int(latest_status_value), "not_reviewed")
        if latest_status_value is not None else None
    )
    # ``dict.get(None)`` is None, no need for an extra None-check guard.
    latest_grade_status = _GRADING_STATUS_LOOKUP.get(qr.latest_grade_status_int)

    submission_group_payload, submission_group_detail = _build_submission_group_payloads(
        submission_group,
        repository=repository,
        submission_status=submission_status,
        submission_grading=latest_grading_value,
        submission_count=qr.submission_count or 0,
        unread=unread,
        graded_by_course_member_payload=graded_by_course_member_payload,
        gradings_payload=gradings_payload,
        detailed=detailed,
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
        submitted=qr.submission_count not in (None, 0),
        course_content_type=CourseContentTypeList.model_validate(course_content.course_content_type),
        result_count=qr.result_count or 0,
        submission_count=qr.submission_count or 0,
        max_test_runs=course_content.max_test_runs,
        testing_service_id=str(course_content.testing_service_id) if course_content.testing_service_id else None,
        directory=directory,
        color=course_content.course_content_type.color,
        result=result_payload,
        submission_group=submission_group_payload,
        unread_message_count=unread,
        deployment=deployment_payload,
        has_deployment=has_deployment,
        # Status: for submittable contents this comes from submission_group;
        # for units it gets aggregated later by the view repository.
        status=submission_status,
        unreviewed_count=qr.is_latest_unreviewed or 0,
        latest_grade_status=latest_grade_status,
    )

    if not detailed:
        return list_obj

    # Get DTO is List + a few extra fields, with richer ``course_content_type``
    # and ``submission_group`` variants. ``model_dump(exclude=...)`` lets us
    # share the common fields without restating every assignment.
    list_data = list_obj.model_dump(exclude={'course_content_type', 'submission_group'})
    return CourseContentStudentGet(
        **list_data,
        created_at=course_content.created_at,
        updated_at=course_content.updated_at,
        archived_at=course_content.archived_at,
        description=course_content.description,
        course_content_type=CourseContentTypeGet.model_validate(course_content.course_content_type),
        submission_group=submission_group_detail,
    )
