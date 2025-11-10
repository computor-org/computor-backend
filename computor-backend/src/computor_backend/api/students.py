import logging
from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends

from computor_backend.permissions.principal import Principal
from computor_backend.permissions.auth import get_current_principal
from computor_backend.redis_cache import get_cache
from computor_backend.cache import Cache
from computor_types.student_course_contents import (
    CourseContentStudentList,
    CourseContentStudentQuery,
    CourseContentStudentGet,
)
from computor_types.student_courses import CourseStudentGet, CourseStudentList, CourseStudentQuery

# Import business logic functions
from computor_backend.business_logic.students import (
    get_student_course_content,
    list_student_course_contents,
    list_student_courses,
    get_student_course,
)

student_router = APIRouter()
logger = logging.getLogger(__name__)

## MR-based course-content messages removed (deprecated)

@student_router.get("/course-contents/{course_content_id}", response_model=CourseContentStudentGet)
async def student_get_course_content_endpoint(
    course_content_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    cache: Cache = Depends(get_cache)
):
    return await get_student_course_content(
        course_content_id=course_content_id,
        user_id=permissions.get_user_id_or_throw(),
        cache=cache,
    )

@student_router.get("/course-contents", response_model=list[CourseContentStudentList])
async def student_list_course_contents_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseContentStudentQuery = Depends(),
    cache: Cache = Depends(get_cache)
):
    return await list_student_course_contents(
        user_id=permissions.get_user_id_or_throw(),
        params=params,
        cache=cache,
    )

@student_router.get("/courses", response_model=list[CourseStudentList])
def student_list_courses_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseStudentQuery = Depends(),
    cache: Cache = Depends(get_cache)
):
    return list_student_courses(
        permissions=permissions,
        params=params,
        cache=cache,
    )

@student_router.get("/courses/{course_id}", response_model=CourseStudentGet)
def student_get_course_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    cache: Cache = Depends(get_cache)
):
    return get_student_course(
        course_id=course_id,
        permissions=permissions,
        cache=cache,
    )