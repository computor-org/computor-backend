"""Business logic for lecturer-specific operations."""
import logging
from uuid import UUID
from typing import List, Optional

from sqlalchemy.orm import Session

from ctutor_backend.repositories.lecturer_view import LecturerViewRepository
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.cache import Cache
from ctutor_backend.interface.courses import CourseList, CourseQuery
from ctutor_backend.interface.lecturer_course_contents import (
    CourseContentLecturerGet,
    CourseContentLecturerList,
    CourseContentLecturerQuery,
)
from ctutor_backend.model.course import Course

logger = logging.getLogger(__name__)


def get_lecturer_course(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> Course:
    """Get a specific course for lecturers with caching via repository."""
    repo = LecturerViewRepository(db, cache)
    return repo.get_course(course_id, permissions)


def list_lecturer_courses(
    permissions: Principal,
    params: CourseQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[CourseList]:
    """List courses accessible to lecturers with caching via repository."""
    repo = LecturerViewRepository(db, cache)
    return repo.list_courses(permissions, params)


def get_lecturer_course_content(
    course_content_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> CourseContentLecturerGet:
    """Get a specific course content with course repository information and caching via repository."""
    repo = LecturerViewRepository(db, cache)
    return repo.get_course_content(course_content_id, permissions)


def list_lecturer_course_contents(
    permissions: Principal,
    params: CourseContentLecturerQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[CourseContentLecturerList]:
    """List course contents with course repository information and caching via repository."""
    repo = LecturerViewRepository(db, cache)
    return repo.list_course_contents(permissions, params)
