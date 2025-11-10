"""Business logic for lecturer-specific operations."""
import logging
from uuid import UUID
from typing import List, Optional

from sqlalchemy.orm import Session

from computor_backend.repositories.lecturer_view import LecturerViewRepository
from computor_backend.permissions.principal import Principal
from computor_backend.cache import Cache
from computor_types.courses import CourseList, CourseQuery
from computor_types.lecturer_course_contents import (
    CourseContentLecturerGet,
    CourseContentLecturerList,
    CourseContentLecturerQuery,
)
from computor_backend.model.course import Course

logger = logging.getLogger(__name__)


def get_lecturer_course(
    course_id: UUID | str,
    permissions: Principal,
    cache: Optional[Cache] = None,
) -> Course:
    """Get a specific course for lecturers with caching via repository."""
    repo = LecturerViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        return repo.get_course(course_id, permissions)
    finally:
        repo.close()


def list_lecturer_courses(
    permissions: Principal,
    params: CourseQuery,
    cache: Optional[Cache] = None,
) -> List[CourseList]:
    """List courses accessible to lecturers with caching via repository."""
    repo = LecturerViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        return repo.list_courses(permissions, params)
    finally:
        repo.close()


def get_lecturer_course_content(
    course_content_id: UUID | str,
    permissions: Principal,
    cache: Optional[Cache] = None,
) -> CourseContentLecturerGet:
    """Get a specific course content with course repository information and caching via repository."""
    repo = LecturerViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        return repo.get_course_content(course_content_id, permissions)
    finally:
        repo.close()


def list_lecturer_course_contents(
    permissions: Principal,
    params: CourseContentLecturerQuery,
    cache: Optional[Cache] = None,
) -> List[CourseContentLecturerList]:
    """List course contents with course repository information and caching via repository."""
    repo = LecturerViewRepository(cache=cache, user_id=permissions.get_user_id_or_throw())
    try:
        return repo.list_course_contents(permissions, params)
    finally:
        repo.close()
