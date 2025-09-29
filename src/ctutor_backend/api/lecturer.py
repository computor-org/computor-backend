from uuid import UUID
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from ctutor_backend.database import get_db
from ctutor_backend.interface.courses import CourseGet, CourseInterface, CourseList, CourseQuery
from ctutor_backend.interface.lecturer_course_contents import (
    CourseContentLecturerGet,
    CourseContentLecturerList,
    CourseContentLecturerQuery,
    CourseContentLecturerInterface
)
from ctutor_backend.permissions.auth import get_current_permissions
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.api.exceptions import NotFoundException
from ctutor_backend.model.course import Course, CourseContent
lecturer_router = APIRouter()

@lecturer_router.get("/courses/{course_id}", response_model=CourseGet)
async def lecturer_get_courses(course_id: UUID | str, permissions: Annotated[Principal, Depends(get_current_permissions)], db: Session = Depends(get_db)):

    course = check_course_permissions(permissions,Course,"_lecturer",db).filter(Course.id == course_id).first()

    if course == None:
        raise NotFoundException()

    return course

@lecturer_router.get("/courses", response_model=list[CourseList])
def lecturer_list_courses(permissions: Annotated[Principal, Depends(get_current_permissions)], params: CourseQuery = Depends(), db: Session = Depends(get_db)):

    query = check_course_permissions(permissions,Course,"_lecturer",db)

    return CourseInterface.search(db,query,params)

@lecturer_router.get("/course-contents/{course_content_id}", response_model=CourseContentLecturerGet)
def lecturer_get_course_contents(course_content_id: UUID | str, permissions: Annotated[Principal, Depends(get_current_permissions)], db: Session = Depends(get_db)):
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


@lecturer_router.get("/course-contents", response_model=list[CourseContentLecturerList])
def lecturer_list_course_contents(permissions: Annotated[Principal, Depends(get_current_permissions)], params: CourseContentLecturerQuery = Depends(), db: Session = Depends(get_db)):
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
