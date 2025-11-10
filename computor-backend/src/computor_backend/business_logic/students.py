"""Business logic for student-specific operations."""
import logging
from uuid import UUID
from typing import List, Optional

from sqlalchemy.orm import Session

from computor_backend.repositories.student_view import StudentViewRepository
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
    cache: Optional[Cache] = None,
) -> CourseContentStudentGet:
    """Get detailed course content for a student with caching via repository."""
    repo = StudentViewRepository(cache=cache, user_id=user_id)
    try:
        return await repo.get_course_content(user_id, course_content_id)
    finally:
        repo.close()


async def list_student_course_contents(
    user_id: str,
    params: CourseContentStudentQuery,
    cache: Optional[Cache] = None,
) -> List[CourseContentStudentList]:
    """List course contents for a student with caching via repository."""
    repo = StudentViewRepository(cache=cache, user_id=user_id)
    try:
        return await repo.list_course_contents(user_id, params)
    finally:
        repo.close()


def list_student_courses(
    permissions: Principal,
    params: CourseStudentQuery,
    cache: Optional[Cache] = None,
) -> List[CourseStudentList]:
    """List courses accessible to a student with caching via repository."""
    repo = StudentViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        return repo.list_courses(permissions, params)
    finally:
        repo.close()


def get_student_course(
    course_id: UUID | str,
    permissions: Principal,
    cache: Optional[Cache] = None,
) -> CourseStudentGet:
    """Get detailed course information for a student with caching via repository."""
    repo = StudentViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        return repo.get_course(course_id, permissions)
    finally:
        repo.close()
