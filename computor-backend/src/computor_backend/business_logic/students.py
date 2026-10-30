"""Business logic for student-specific operations."""
import logging
from uuid import UUID
from typing import List, Optional

from sqlalchemy.orm import Session

from computor_backend.repositories.student_view import StudentViewRepository
from computor_backend.business_logic.localization import localize_dto
from computor_backend.permissions.principal import Principal
from computor_backend.cache import Cache
from computor_types.student_course_contents import (
    CourseContentStudentList,
    CourseContentStudentQuery,
    CourseContentStudentGet,
)
from computor_types.student_courses import (
    CourseStudentGet,
    CourseStudentList,
    CourseStudentQuery,
)

logger = logging.getLogger(__name__)


async def get_student_course_content(
    course_content_id: UUID | str,
    user_id: str,
    permissions: Optional[Principal] = None,
    cache: Optional[Cache] = None,
    lang: Optional[str] = None,
) -> CourseContentStudentGet:
    """Get detailed course content for a student with caching via repository.

    ``permissions`` is needed to tell a real student from a lecturer or tutor
    walking the same view: staff keep seeing content hidden from students
    (issue #338). ``lang`` resolves title and description after the cache,
    so one cache entry serves every language (issue #550).
    """
    repo = StudentViewRepository(cache=cache, user_id=user_id)
    try:
        dto = await repo.get_course_content(user_id, course_content_id, permissions)
    finally:
        repo.close()
    return localize_dto(dto, lang)


async def list_student_course_contents(
    user_id: str,
    params: CourseContentStudentQuery,
    permissions: Optional[Principal] = None,
    cache: Optional[Cache] = None,
    lang: Optional[str] = None,
) -> List[CourseContentStudentList]:
    """List course contents for a student with caching via repository."""
    repo = StudentViewRepository(cache=cache, user_id=user_id)
    try:
        rows = await repo.list_course_contents(user_id, params, permissions)
    finally:
        repo.close()
    return [localize_dto(row, lang) for row in rows]


def list_student_courses(
    permissions: Principal,
    params: CourseStudentQuery,
    cache: Optional[Cache] = None,
    lang: Optional[str] = None,
) -> List[CourseStudentList]:
    """List courses accessible to a student with caching via repository."""
    repo = StudentViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        rows = repo.list_courses(permissions, params)
    finally:
        repo.close()
    return [localize_dto(row, lang) for row in rows]


def get_student_course(
    course_id: UUID | str,
    permissions: Principal,
    cache: Optional[Cache] = None,
    lang: Optional[str] = None,
) -> CourseStudentGet:
    """Get detailed course information for a student with caching via repository."""
    repo = StudentViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        dto = repo.get_course(course_id, permissions)
    finally:
        repo.close()
    return localize_dto(dto, lang)
