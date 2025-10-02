"""Business logic for tutor-specific operations."""
import logging
from uuid import UUID
from typing import List, Tuple, Optional
from aiocache import SimpleMemoryCache

from sqlalchemy import desc
from sqlalchemy.orm import Session

from ctutor_backend.api.exceptions import ForbiddenException, NotFoundException
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal, allowed_course_role_ids
from ctutor_backend.model.auth import User
from ctutor_backend.model.course import (
    Course,
    CourseContent,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from ctutor_backend.model.artifact import SubmissionArtifact, SubmissionGrade
from ctutor_backend.api.mappers import course_member_course_content_result_mapper
from ctutor_backend.api.queries import (
    course_course_member_list_query,
    course_member_course_content_list_query,
    course_member_course_content_query,
)
from ctutor_backend.interface.student_courses import CourseStudentInterface, CourseStudentQuery
from ctutor_backend.interface.student_course_contents import CourseContentStudentInterface, CourseContentStudentQuery
from ctutor_backend.interface.course_members import CourseMemberInterface, CourseMemberQuery
from ctutor_backend.interface.tutor_courses import CourseTutorGet, CourseTutorList, CourseTutorRepository
from ctutor_backend.interface.tutor_course_members import TutorCourseMemberCourseContent, TutorCourseMemberGet, TutorCourseMemberList
from ctutor_backend.interface.grading import GradingStatus

logger = logging.getLogger(__name__)

_tutor_cache = SimpleMemoryCache()
_expiry_time_tutors = 3600  # in seconds


async def get_cached_data(course_id: str):
    """Get cached tutor data for a course."""
    cached = await _tutor_cache.get(f"{course_id}")
    if cached is not None:
        return cached
    return None


async def set_cached_data(course_id: str, data: dict):
    """Set cached tutor data for a course."""
    await _tutor_cache.set(f"{course_id}", data, _expiry_time_tutors)


def get_tutor_course_content(
    course_member_id: UUID | str,
    course_content_id: UUID | str,
    permissions: Principal,
    db: Session,
):
    """Get course content for a course member as a tutor."""

    if check_course_permissions(permissions, CourseMember, "_tutor", db).filter(
        CourseMember.id == course_member_id
    ).first() is None:
        raise ForbiddenException()

    reader_user_id = permissions.get_user_id_or_throw()
    course_contents_result = course_member_course_content_query(
        course_member_id, course_content_id, db, reader_user_id=reader_user_id
    )

    return course_member_course_content_result_mapper(course_contents_result, db, detailed=True)


def list_tutor_course_contents(
    course_member_id: UUID | str,
    permissions: Principal,
    params: CourseContentStudentQuery,
    db: Session,
):
    """List course contents for a course member as a tutor."""

    if check_course_permissions(permissions, CourseMember, "_tutor", db).filter(
        CourseMember.id == course_member_id
    ).first() is None:
        raise ForbiddenException()

    reader_user_id = permissions.get_user_id_or_throw()
    query = course_member_course_content_list_query(course_member_id, db, reader_user_id=reader_user_id)

    course_contents_results = CourseContentStudentInterface.search(db, query, params).all()

    response_list = []
    for course_contents_result in course_contents_results:
        response_list.append(course_member_course_content_result_mapper(course_contents_result, db))

    return response_list


def update_tutor_course_content_grade(
    course_member_id: UUID | str,
    course_content_id: UUID | str,
    grade_value: Optional[float],
    grading_status: Optional[GradingStatus],
    feedback: Optional[str],
    artifact_id: Optional[UUID | str],
    permissions: Principal,
    db: Session,
):
    """Update grade for a course content as a tutor."""

    if check_course_permissions(permissions, CourseMember, "_tutor", db).filter(
        CourseMember.id == course_member_id
    ).first() is None:
        raise ForbiddenException()

    # 1) Resolve the student's course member and related submission group for this content
    student_cm = db.query(CourseMember).filter(CourseMember.id == course_member_id).first()
    if student_cm is None:
        raise NotFoundException()

    submission_group = (
        db.query(SubmissionGroup)
        .join(
            SubmissionGroupMember,
            SubmissionGroupMember.submission_group_id == SubmissionGroup.id,
        )
        .filter(
            SubmissionGroupMember.course_member_id == course_member_id,
            SubmissionGroup.course_content_id == course_content_id,
        )
        .first()
    )

    if submission_group is None:
        raise NotFoundException()

    # 2) Resolve the grader's course member (the current user in the same course)
    grader_cm = (
        db.query(CourseMember)
        .filter(
            CourseMember.user_id == permissions.get_user_id_or_throw(),
            CourseMember.course_id == student_cm.course_id,
        )
        .first()
    )
    if grader_cm is None:
        raise ForbiddenException()

    # 3) Determine which artifact to grade
    if artifact_id:
        # Specific artifact requested - verify it belongs to this submission group
        artifact_to_grade = (
            db.query(SubmissionArtifact)
            .filter(
                SubmissionArtifact.id == artifact_id,
                SubmissionArtifact.submission_group_id == submission_group.id
            )
            .first()
        )
        if artifact_to_grade is None:
            raise NotFoundException(detail="Specified artifact not found or doesn't belong to this submission group")
    else:
        # Get the latest submission artifact for this submission group
        artifact_to_grade = (
            db.query(SubmissionArtifact)
            .filter(SubmissionArtifact.submission_group_id == submission_group.id)
            .order_by(SubmissionArtifact.created_at.desc())
            .first()
        )
        if artifact_to_grade is None:
            raise NotFoundException(detail="No submission artifact found for this submission group. Student must submit first.")

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

    # 6) Return fresh data
    reader_user_id = permissions.get_user_id_or_throw()
    course_contents_result = course_member_course_content_query(
        course_member_id, course_content_id, db, reader_user_id=reader_user_id
    )

    response = course_member_course_content_result_mapper(course_contents_result, db)

    # Add artifact info
    return {
        "response": response,
        "graded_artifact_id": artifact_to_grade.id,
        "graded_artifact_info": {
            "id": str(artifact_to_grade.id),
            "created_at": artifact_to_grade.created_at.isoformat() if artifact_to_grade.created_at else None,
            "properties": artifact_to_grade.properties,
        }
    }


def get_tutor_course(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> CourseTutorGet:
    """Get a course for tutors."""

    course = check_course_permissions(permissions, Course, "_tutor", db).filter(
        Course.id == course_id
    ).first()

    if course is None:
        raise NotFoundException()

    return CourseTutorGet(
        id=str(course.id),
        title=course.title,
        course_family_id=str(course.course_family_id) if course.course_family_id else None,
        organization_id=str(course.organization_id) if course.organization_id else None,
        path=course.path,
        repository=CourseTutorRepository(
            provider_url=course.properties.get("gitlab", {}).get("url") if course.properties else None,
            full_path_reference=f'{course.properties.get("gitlab", {}).get("full_path", "")}/reference' if course.properties and course.properties.get("gitlab", {}).get("full_path") else None
        ) if course.properties and course.properties.get("gitlab") else None
    )


def list_tutor_courses(
    permissions: Principal,
    params: CourseStudentQuery,
    db: Session,
) -> List[CourseTutorList]:
    """List courses for tutors."""

    query = check_course_permissions(permissions, Course, "_tutor", db)
    courses = CourseStudentInterface.search(db, query, params).all()

    response_list = []
    for course in courses:
        response_list.append(CourseTutorList(
            id=str(course.id),
            title=course.title,
            course_family_id=str(course.course_family_id) if course.course_family_id else None,
            organization_id=str(course.organization_id) if course.organization_id else None,
            path=course.path,
            repository=CourseTutorRepository(
                provider_url=course.properties.get("gitlab", {}).get("url") if course.properties else None,
                full_path_reference=f'{course.properties.get("gitlab", {}).get("full_path", "")}/reference' if course.properties and course.properties.get("gitlab", {}).get("full_path") else None
            ) if course.properties and course.properties.get("gitlab") else None
        ))

    return response_list


def get_tutor_course_member(
    course_member_id: UUID | str,
    permissions: Principal,
    db: Session,
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
