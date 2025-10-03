import logging
from uuid import UUID
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from ctutor_backend.permissions.principal import Principal
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.database import get_db
from ctutor_backend.redis_cache import get_cache
from ctutor_backend.cache import Cache
from ctutor_backend.interface.student_course_contents import (
    CourseContentStudentList,
    CourseContentStudentQuery,
    CourseContentStudentGet,
)
from ctutor_backend.interface.student_courses import CourseStudentGet, CourseStudentList, CourseStudentQuery

# Import business logic functions
from ctutor_backend.business_logic.students import (
    get_student_course_content,
    list_student_course_contents,
    list_student_courses,
    get_student_course,
)

student_router = APIRouter()
logger = logging.getLogger(__name__)

## MR-based course-content messages removed (deprecated)

@student_router.get("/course-contents/{course_content_id}", response_model=CourseContentStudentGet)
def student_get_course_content_endpoint(
    course_content_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    return get_student_course_content(
        course_content_id=course_content_id,
        user_id=permissions.get_user_id_or_throw(),
        db=db,
        cache=cache,
    )

@student_router.get("/course-contents", response_model=list[CourseContentStudentList])
def student_list_course_contents_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseContentStudentQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    return list_student_course_contents(
        user_id=permissions.get_user_id_or_throw(),
        params=params,
        db=db,
        cache=cache,
    )

@student_router.get("/courses", response_model=list[CourseStudentList])
def student_list_courses_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseStudentQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    return list_student_courses(
        permissions=permissions,
        params=params,
        db=db,
        cache=cache,
    )

@student_router.get("/courses/{course_id}", response_model=CourseStudentGet)
def student_get_course_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    return get_student_course(
        course_id=course_id,
        permissions=permissions,
        db=db,
        cache=cache,
    )