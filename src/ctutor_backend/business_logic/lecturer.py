"""Business logic for lecturer-specific operations."""
import logging
from uuid import UUID
from typing import List

from sqlalchemy.orm import Session

from ctutor_backend.api.exceptions import NotFoundException
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.interface.courses import CourseInterface, CourseList, CourseQuery
from ctutor_backend.interface.lecturer_course_contents import (
    CourseContentLecturerGet,
    CourseContentLecturerList,
    CourseContentLecturerQuery,
    CourseContentLecturerInterface
)
from ctutor_backend.model.course import Course, CourseContent

logger = logging.getLogger(__name__)


def get_lecturer_course(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> Course:
    """Get a specific course for lecturers."""

    course = check_course_permissions(permissions, Course, "_lecturer", db).filter(
        Course.id == course_id
    ).first()

    if course is None:
        raise NotFoundException()

    return course


def list_lecturer_courses(
    permissions: Principal,
    params: CourseQuery,
    db: Session,
) -> List[CourseList]:
    """List courses accessible to lecturers."""

    query = check_course_permissions(permissions, Course, "_lecturer", db)

    return CourseInterface.search(db, query, params)


def get_lecturer_course_content(
    course_content_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> CourseContentLecturerGet:
    """Get a specific course content with course repository information."""

    # Check permissions and get course content
    course_content = check_course_permissions(
        permissions, CourseContent, "_lecturer", db
    ).filter(CourseContent.id == course_content_id).first()

    if course_content is None:
        raise NotFoundException()

    # Get the course to extract GitLab repository information
    course = db.query(Course).filter(Course.id == course_content.course_id).first()

    # Build response with course repository info
    response_dict = {
        **course_content.__dict__,
        "repository": {
            "url": course.properties.get("gitlab", {}).get("url") if course.properties else None,
            "full_path": course.properties.get("gitlab", {}).get("full_path") if course.properties else None
        }
    }

    return CourseContentLecturerGet.model_validate(response_dict)


def list_lecturer_course_contents(
    permissions: Principal,
    params: CourseContentLecturerQuery,
    db: Session,
) -> List[CourseContentLecturerList]:
    """List course contents with course repository information."""

    # Check permissions
    query = check_course_permissions(
        permissions, CourseContent, "_lecturer", db
    )

    # Apply search filters
    course_contents = CourseContentLecturerInterface.search(db, query, params)

    # Build response with course repository info for each item
    result = []
    for course_content in course_contents:
        # Get the course to extract GitLab repository information
        course = db.query(Course).filter(Course.id == course_content.course_id).first()

        response_dict = {
            **course_content.__dict__,
            "repository": {
                "url": course.properties.get("gitlab", {}).get("url") if course.properties else None,
                "full_path": course.properties.get("gitlab", {}).get("full_path") if course.properties else None
            }
        }

        result.append(CourseContentLecturerList.model_validate(response_dict))

    return result
