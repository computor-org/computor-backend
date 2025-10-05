"""Business logic for student-specific operations."""
import logging
from uuid import UUID
from typing import List, Optional

from sqlalchemy.orm import Session

from ctutor_backend.repositories.student_view import StudentViewRepository
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.cache import Cache
from ctutor_backend.interface.student_course_contents import (
    CourseContentStudentList,
    CourseContentStudentQuery,
    CourseContentStudentGet,
)
from ctutor_backend.interface.student_courses import (
    CourseStudentGet,
    CourseStudentList,
    CourseStudentQuery,
)

logger = logging.getLogger(__name__)


def get_student_course_content(
    course_content_id: UUID | str,
    user_id: str,
    db: Session,
    cache: Optional[Cache] = None,
) -> CourseContentStudentGet:
    """Get detailed course content for a student with caching via repository."""
    repo = StudentViewRepository(db, cache)
    return repo.get_course_content(user_id, course_content_id)


def list_student_course_contents(
    user_id: str,
    params: CourseContentStudentQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[CourseContentStudentList]:
    """List course contents for a student with caching via repository."""
    repo = StudentViewRepository(db, cache)
    return repo.list_course_contents(user_id, params)


def list_student_courses(
    permissions: Principal,
    params: CourseStudentQuery,
    db: Session,
    cache: Optional[Cache] = None,
) -> List[CourseStudentList]:
    """List courses accessible to a student with caching via repository."""
    repo = StudentViewRepository(db, cache)
    return repo.list_courses(permissions, params)


def get_student_course(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
    cache: Optional[Cache] = None,
) -> CourseStudentGet:
    """Get detailed course information for a student with caching via repository."""
    repo = StudentViewRepository(db, cache)
    return repo.get_course(course_id, permissions)
