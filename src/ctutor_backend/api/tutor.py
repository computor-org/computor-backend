from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ctutor_backend.database import get_db
from ctutor_backend.redis_cache import get_cache
from ctutor_backend.cache import Cache
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.interface.student_courses import CourseStudentQuery
from ctutor_backend.interface.student_course_contents import (
    CourseContentStudentList,
    CourseContentStudentQuery,
    CourseContentStudentGet,
)
from ctutor_backend.interface.tutor_course_members import TutorCourseMemberGet, TutorCourseMemberList
from ctutor_backend.interface.tutor_courses import CourseTutorGet, CourseTutorList
from ctutor_backend.interface.tutor_grading import TutorGradeCreate, TutorGradeResponse
from ctutor_backend.interface.course_members import CourseMemberQuery

# Import business logic
from ctutor_backend.business_logic.tutor import (
    get_tutor_course_content,
    list_tutor_course_contents,
    update_tutor_course_content_grade,
    get_tutor_course,
    list_tutor_courses,
    get_tutor_course_member,
    list_tutor_course_members,
)

tutor_router = APIRouter()


@tutor_router.get("/course-members/{course_member_id}/course-contents/{course_content_id}", response_model=CourseContentStudentGet)
def tutor_get_course_contents_endpoint(
    course_content_id: UUID | str,
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Get course content for a course member as a tutor."""
    return get_tutor_course_content(course_member_id, course_content_id, permissions, db, cache)


@tutor_router.get("/course-members/{course_member_id}/course-contents", response_model=list[CourseContentStudentList])
def tutor_list_course_contents_endpoint(
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseContentStudentQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """List course contents for a course member as a tutor."""
    return list_tutor_course_contents(course_member_id, permissions, params, db, cache)


@tutor_router.patch("/course-members/{course_member_id}/course-contents/{course_content_id}", response_model=TutorGradeResponse)
def tutor_update_course_contents_endpoint(
    course_content_id: UUID | str,
    course_member_id: UUID | str,
    grade_data: TutorGradeCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Update grade for a course content as a tutor."""
    return update_tutor_course_content_grade(
        course_member_id=course_member_id,
        course_content_id=course_content_id,
        grade_value=grade_data.grade,
        grading_status=grade_data.status,
        feedback=grade_data.feedback,
        artifact_id=grade_data.artifact_id,
        permissions=permissions,
        db=db,
        cache=cache,
    )


@tutor_router.get("/courses/{course_id}", response_model=CourseTutorGet)
def tutor_get_courses_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Get a course for tutors."""
    return get_tutor_course(course_id, permissions, db, cache)


@tutor_router.get("/courses", response_model=list[CourseTutorList])
def tutor_list_courses_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseStudentQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """List courses for tutors."""
    return list_tutor_courses(permissions, params, db, cache)


@tutor_router.get("/course-members/{course_member_id}", response_model=TutorCourseMemberGet)
def tutor_get_course_members_endpoint(
    course_member_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Get a course member with unreviewed course contents."""
    return get_tutor_course_member(course_member_id, permissions, db, cache)


@tutor_router.get("/course-members", response_model=list[TutorCourseMemberList])
def tutor_list_course_members_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseMemberQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """List course members for tutors."""
    return list_tutor_course_members(permissions, params, db, cache)


## MR-based course-content messages removed (deprecated)

## Comments routes moved to generic /course-member-comments
