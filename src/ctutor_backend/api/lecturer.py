from uuid import UUID
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from ctutor_backend.database import get_db
from ctutor_backend.interface.courses import CourseGet, CourseList, CourseQuery
from ctutor_backend.interface.lecturer_course_contents import (
    CourseContentLecturerGet,
    CourseContentLecturerList,
    CourseContentLecturerQuery,
)
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.principal import Principal

# Import business logic
from ctutor_backend.business_logic.lecturer import (
    get_lecturer_course,
    list_lecturer_courses,
    get_lecturer_course_content,
    list_lecturer_course_contents,
)

lecturer_router = APIRouter()


@lecturer_router.get("/courses/{course_id}", response_model=CourseGet)
async def lecturer_get_courses_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """Get a specific course for lecturers."""
    return get_lecturer_course(course_id, permissions, db)


@lecturer_router.get("/courses", response_model=list[CourseList])
def lecturer_list_courses_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseQuery = Depends(),
    db: Session = Depends(get_db)
):
    """List courses accessible to lecturers."""
    return list_lecturer_courses(permissions, params, db)


@lecturer_router.get("/course-contents/{course_content_id}", response_model=CourseContentLecturerGet)
def lecturer_get_course_contents_endpoint(
    course_content_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """Get a specific course content with course repository information."""
    return get_lecturer_course_content(course_content_id, permissions, db)


@lecturer_router.get("/course-contents", response_model=list[CourseContentLecturerList])
def lecturer_list_course_contents_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseContentLecturerQuery = Depends(),
    db: Session = Depends(get_db)
):
    """List course contents with course repository information."""
    return list_lecturer_course_contents(permissions, params, db)
