"""Business logic for student-specific operations."""
import json
import logging
from uuid import UUID
from typing import List

from sqlalchemy.orm import Session
from aiocache import BaseCache

from ctutor_backend.api.exceptions import NotFoundException
from ctutor_backend.api.mappers import course_member_course_content_result_mapper
from ctutor_backend.repositories.course_content import user_course_content_list_query, user_course_content_query
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.interface.course_contents import CourseContentGet
from ctutor_backend.interface.student_course_contents import (
    CourseContentStudentInterface,
    CourseContentStudentList,
    CourseContentStudentQuery,
    CourseContentStudentGet,
)
from ctutor_backend.interface.student_courses import (
    CourseStudentGet,
    CourseStudentInterface,
    CourseStudentList,
    CourseStudentQuery,
    CourseStudentRepository,
)
from ctutor_backend.model.course import Course, CourseContent

logger = logging.getLogger(__name__)


async def get_course_content_cached(
    course_content_id: str,
    permissions: Principal,
    cache: BaseCache,
    db: Session
) -> CourseContentGet:
    """Get course content with caching support."""

    cache_key = f"{permissions.get_user_id_or_throw()}:course-contents:{course_content_id}"

    course_content = await cache.get(cache_key)

    if course_content is not None:
        return CourseContentGet.model_validate(json.loads(course_content), from_attributes=True)

    query = check_course_permissions(permissions, CourseContent, "_student", db).filter(
        CourseContent.id == course_content_id
    ).first()

    if query is None:
        raise NotFoundException()

    course_content = CourseContentGet.model_validate(query, from_attributes=True)

    try:
        await cache.set(cache_key, course_content.model_dump_json(), ttl=120)
    except Exception as e:
        raise e

    return course_content


def get_student_course_content(
    course_content_id: UUID | str,
    user_id: str,
    db: Session,
) -> CourseContentStudentGet:
    """Get detailed course content for a student."""

    course_contents_result = user_course_content_query(user_id, course_content_id, db)

    return course_member_course_content_result_mapper(course_contents_result, db, detailed=True)


def list_student_course_contents(
    user_id: str,
    params: CourseContentStudentQuery,
    db: Session,
) -> List[CourseContentStudentList]:
    """List course contents for a student."""

    query = user_course_content_list_query(user_id, db)

    course_contents_results = CourseContentStudentInterface.search(db, query, params).all()

    response_list: List[CourseContentStudentList] = []

    for course_contents_result in course_contents_results:
        response_list.append(course_member_course_content_result_mapper(course_contents_result, db))

    return response_list


def list_student_courses(
    permissions: Principal,
    params: CourseStudentQuery,
    db: Session,
) -> List[CourseStudentList]:
    """List courses accessible to a student."""

    courses = CourseStudentInterface.search(
        db,
        check_course_permissions(permissions, Course, "_student", db),
        params
    ).all()

    response_list: List[CourseStudentList] = []

    for course in courses:
        response_list.append(CourseStudentList(
            id=course.id,
            title=course.title,
            course_family_id=course.course_family_id,
            organization_id=course.organization_id,
            path=course.path,
            repository=CourseStudentRepository(
                provider_url=course.properties.get("gitlab", {}).get("url") if course.properties else None,
                full_path=course.properties.get("gitlab", {}).get("full_path") if course.properties else None
            ) if course.properties and course.properties.get("gitlab") else None
        ))

    return response_list


def get_student_course(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> CourseStudentGet:
    """Get detailed course information for a student."""

    course = check_course_permissions(permissions, Course, "_student", db).filter(
        Course.id == course_id
    ).first()

    return CourseStudentGet(
        id=course.id,
        title=course.title,
        course_family_id=course.course_family_id,
        organization_id=course.organization_id,
        course_content_types=course.course_content_types,
        path=course.path,
        repository=CourseStudentRepository(
            provider_url=course.properties.get("gitlab", {}).get("url") if course.properties else None,
            full_path=course.properties.get("gitlab", {}).get("full_path") if course.properties else None
        ) if course.properties and course.properties.get("gitlab") else None
    )
