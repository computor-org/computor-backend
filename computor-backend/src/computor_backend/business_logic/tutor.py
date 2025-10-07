"""Business logic for tutor-specific operations."""
import logging
from uuid import UUID
from typing import List, Optional

from sqlalchemy.orm import Session

from computor_backend.api.exceptions import ForbiddenException, NotFoundException
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal, allowed_course_role_ids
from computor_backend.cache import Cache
from computor_backend.repositories.tutor_view import TutorViewRepository
from computor_backend.repositories.course_member import CourseMemberRepository
from computor_backend.repositories.submission_group import SubmissionGroupRepository
from computor_backend.repositories.submission_artifact import SubmissionArtifactRepository
from computor_backend.repositories.course_content import (
    course_course_member_list_query,
    course_member_course_content_list_query,
    course_member_course_content_query,
)
from computor_backend.api.mappers import course_member_course_content_result_mapper
from computor_backend.model.auth import User
from computor_backend.model.course import Course, CourseMember, SubmissionGroup, SubmissionGroupMember
from computor_backend.model.artifact import SubmissionArtifact, SubmissionGrade
from computor_types.student_courses import CourseStudentQuery
from computor_types.student_course_contents import CourseContentStudentQuery
from computor_types.course_members import CourseMemberQuery
from computor_backend.interfaces.course_member import CourseMemberInterface
from computor_types.tutor_courses import CourseTutorGet, CourseTutorList
from computor_types.tutor_course_members import TutorCourseMemberCourseContent, TutorCourseMemberGet, TutorCourseMemberList
from computor_types.grading import GradingStatus
from computor_types.tutor_grading import TutorGradeResponse, GradedArtifactInfo

logger = logging.getLogger(__name__)


def get_tutor_course_content(
    course_member_id: UUID | str,
    course_content_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
):
    """Get course content for a course member as a tutor with caching via repository."""
    repo = TutorViewRepository(db, cache)
    return repo.get_course_content(course_member_id, course_content_id, permissions)


def list_tutor_course_contents(
    course_member_id: UUID | str,
    permissions: Principal,
    params: CourseContentStudentQuery,
    db: Session,
    cache: Optional[Cache] = None,
):
    """List course contents for a course member as a tutor with caching via repository."""
    repo = TutorViewRepository(db, cache)
    return repo.list_course_contents(course_member_id, permissions, params)


def update_tutor_course_content_grade(
    course_member_id: UUID | str,
    course_content_id: UUID | str,
    grade_value: Optional[float],
    grading_status: Optional[GradingStatus],
    feedback: Optional[str],
    artifact_id: Optional[UUID | str],
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> TutorGradeResponse:
    """Update grade for a course content as a tutor.

    Args:
        course_member_id: The course member (student) to grade
        course_content_id: The course content being graded
        grade_value: The grade value (0.0 to 1.0)
        grading_status: The grading status
        feedback: Optional feedback comment
        artifact_id: Optional specific artifact to grade (defaults to latest)
        permissions: Current user permissions
        db: Database session
        cache: Optional cache instance

    Returns:
        TutorGradeResponse with updated course content and graded artifact info
    """

    if check_course_permissions(permissions, CourseMember, "_tutor", db).filter(
        CourseMember.id == course_member_id
    ).first() is None:
        raise ForbiddenException()

    # Initialize repositories with cache
    course_member_repo = CourseMemberRepository(db, cache)
    submission_group_repo = SubmissionGroupRepository(db, cache)
    submission_artifact_repo = SubmissionArtifactRepository(db, cache)

    # 1) Resolve the student's course member and related submission group for this content
    student_cm = course_member_repo.get_by_id_optional(course_member_id)
    if student_cm is None:
        raise NotFoundException()

    # Find submission group for this course member and content
    submission_groups = submission_group_repo.find_by_course_content(course_content_id)
    submission_group = None
    for sg in submission_groups:
        # Check if this submission group has the course member
        for member in sg.members:
            if str(member.course_member_id) == str(course_member_id):
                submission_group = sg
                break
        if submission_group:
            break

    if submission_group is None:
        raise NotFoundException()

    # 2) Resolve the grader's course member (the current user in the same course)
    grader_cm = course_member_repo.find_by_user_and_course(
        user_id=permissions.get_user_id_or_throw(),
        course_id=student_cm.course_id
    )
    if grader_cm is None:
        raise ForbiddenException()

    # 3) Determine which artifact to grade
    if artifact_id:
        # Specific artifact requested - verify it belongs to this submission group
        artifact_to_grade = submission_artifact_repo.get_by_id_optional(artifact_id)
        if artifact_to_grade is None or str(artifact_to_grade.submission_group_id) != str(submission_group.id):
            raise NotFoundException(detail="Specified artifact not found or doesn't belong to this submission group")
    else:
        # Get the latest submission artifact for this submission group
        artifacts = submission_artifact_repo.find_by_submission_group(submission_group.id)
        if not artifacts:
            raise NotFoundException(detail="No submission artifact found for this submission group. Student must submit first.")
        artifact_to_grade = max(artifacts, key=lambda a: a.created_at)

    # 4) Get grading status
    status = grading_status if grading_status is not None else GradingStatus.NOT_REVIEWED

    # 5) Create a new artifact-based grade
    if grade_value is not None or grading_status is not None:
        grade = grade_value if grade_value is not None else 0.0

        new_grading = SubmissionGrade(
            artifact_id=artifact_to_grade.id,
            graded_by_course_member_id=grader_cm.id,
            grade=grade,
            status=status.value,
            comment=feedback,
        )
        db.add(new_grading)
        db.commit()

        logger.info(f"Created grade for artifact {artifact_to_grade.id} by grader {grader_cm.id}")

        # Invalidate cached views after grading
        if cache:
            cache.invalidate_user_views(
                entity_type="course_member_id",
                entity_id=str(course_member_id)
            )
            cache.invalidate_user_views(
                entity_type="course_content_id",
                entity_id=str(course_content_id)
            )

    # 6) Return fresh data
    reader_user_id = permissions.get_user_id_or_throw()
    course_contents_result = course_member_course_content_query(
        course_member_id, course_content_id, db, reader_user_id=reader_user_id
    )

    response = course_member_course_content_result_mapper(course_contents_result, db)

    # Build typed artifact info
    artifact_info = GradedArtifactInfo(
        id=str(artifact_to_grade.id),
        created_at=artifact_to_grade.created_at.isoformat() if artifact_to_grade.created_at else None,
        properties=artifact_to_grade.properties,
    )

    # Return typed TutorGradeResponse
    return TutorGradeResponse(
        **response.model_dump(),
        graded_artifact_id=str(artifact_to_grade.id),
        graded_artifact_info=artifact_info,
    )


def get_tutor_course(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> CourseTutorGet:
    """Get a course for tutors with caching via repository."""
    repo = TutorViewRepository(db, cache)
    return repo.get_course(course_id, permissions)


def list_tutor_courses(
    permissions: Principal,
    params: CourseStudentQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[CourseTutorList]:
    """List courses for tutors with caching via repository."""
    repo = TutorViewRepository(db, cache)
    return repo.list_courses(permissions, params)


def get_tutor_course_member(
    course_member_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> TutorCourseMemberGet:
    """Get a course member with unreviewed course contents."""

    course_member = check_course_permissions(permissions, CourseMember, "_tutor", db).filter(
        CourseMember.id == course_member_id
    ).first()

    reader_user_id = permissions.get_user_id_or_throw()
    course_contents_results = course_member_course_content_list_query(course_member_id, db, reader_user_id=reader_user_id).all()

    response_list = []

    for course_contents_result in course_contents_results:
        query = course_contents_result
        course_content = query[0]
        result = query[2]

        if result is not None:
            # Get submit field from associated SubmissionArtifact
            submit = False
            if result.submission_artifact:
                submit = result.submission_artifact.submit
            status = result.status

            todo = True if submit is True and status is None else False
            if todo is True:
                response_list.append(TutorCourseMemberCourseContent(id=course_content.id, path=str(course_content.path)))

    tutor_course_member = TutorCourseMemberGet.model_validate(course_member, from_attributes=True)
    tutor_course_member.unreviewed_course_contents = response_list

    return tutor_course_member


def list_tutor_course_members(
    permissions: Principal,
    params: CourseMemberQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[TutorCourseMemberList]:
    """List course members for tutors."""

    subquery = db.query(Course.id).select_from(User).filter(User.id == permissions.get_user_id_or_throw()) \
        .join(CourseMember, CourseMember.user_id == User.id) \
        .join(Course, Course.id == CourseMember.course_id) \
        .filter(CourseMember.course_role_id.in_((allowed_course_role_ids("_tutor")))).all()

    query = course_course_member_list_query(db)
    query = CourseMemberInterface.search(db, query, params)

    if permissions.is_admin != True:
        query = query.join(Course, Course.id == CourseMember.course_id).filter(
            Course.id.in_([r.id for r in subquery])
        ).join(User, User.id == CourseMember.user_id).order_by(User.family_name).all()

    response_list = []

    for course_member, latest_result_date in query:
        tutor_course_member = TutorCourseMemberList.model_validate(course_member, from_attributes=True)
        tutor_course_member.unreviewed = True if latest_result_date is not None else False
        response_list.append(tutor_course_member)

    return response_list
