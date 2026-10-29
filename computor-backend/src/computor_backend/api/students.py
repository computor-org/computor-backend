import logging
from uuid import UUID
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.services.storage_service import get_storage_service
from computor_backend.business_logic.student_description import get_student_description
from computor_backend.business_logic.localization import LocalizeParam

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

@student_router.get(
    "/course-contents/{course_content_id}/description",
    responses={200: {"content": {"application/zip": {}}}},
)
async def student_get_course_content_description_endpoint(
    course_content_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
    storage_service=Depends(get_storage_service),
):
    return await get_student_description(course_content_id, permissions, db, storage_service)

@student_router.get("/course-contents/{course_content_id}", response_model=CourseContentStudentGet)
async def student_get_course_content_endpoint(
    course_content_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    cache: Cache = Depends(get_cache),
    localize: LocalizeParam = None,
):
    return await get_student_course_content(
        course_content_id=course_content_id,
        user_id=permissions.get_user_id_or_throw(),
        permissions=permissions,
        cache=cache,
        lang=localize,
    )

@student_router.get("/course-contents", response_model=list[CourseContentStudentList])
async def student_list_course_contents_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseContentStudentQuery = Depends(),
    cache: Cache = Depends(get_cache),
    localize: LocalizeParam = None,
):
    return await list_student_course_contents(
        user_id=permissions.get_user_id_or_throw(),
        params=params,
        permissions=permissions,
        cache=cache,
        lang=localize,
    )

@student_router.get("/courses", response_model=list[CourseStudentList])
def student_list_courses_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseStudentQuery = Depends(),
    cache: Cache = Depends(get_cache),
    localize: LocalizeParam = None,
):
    return list_student_courses(
        permissions=permissions,
        params=params,
        cache=cache,
        lang=localize,
    )

@student_router.get("/courses/{course_id}", response_model=CourseStudentGet)
def student_get_course_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    cache: Cache = Depends(get_cache),
    localize: LocalizeParam = None,
):
    return get_student_course(
        course_id=course_id,
        permissions=permissions,
        cache=cache,
        lang=localize,
    )
