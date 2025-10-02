import json
import logging
from uuid import UUID
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from ctutor_backend.api.exceptions import NotFoundException
from ctutor_backend.api.mappers import course_member_course_content_result_mapper
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.api.queries import user_course_content_list_query, user_course_content_query
from ctutor_backend.interface.course_contents import CourseContentGet
from ctutor_backend.interface.student_course_contents import (
    CourseContentStudentInterface,
    CourseContentStudentList,
    CourseContentStudentQuery,
    CourseContentStudentGet,
)
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.database import get_db
from ctutor_backend.interface.student_courses import CourseStudentGet, CourseStudentInterface, CourseStudentList, CourseStudentQuery, CourseStudentRepository
from ctutor_backend.model.course import Course, CourseContent
from aiocache import BaseCache
student_router = APIRouter()
logger = logging.getLogger(__name__)

async def student_get_course_content_cached(course_content_id: str, permissions: Principal, cache: BaseCache, db: Session):

    cache_key = f"{permissions.get_user_id_or_throw()}:course-contents:{course_content_id}"

    course_content = await cache.get(cache_key)

    if course_content != None:
        return CourseContentGet.model_validate(json.loads(course_content),from_attributes=True)

    query = check_course_permissions(permissions,CourseContent,"_student",db).filter(CourseContent.id == course_content_id).first()

    if query == None:
        raise NotFoundException()
    
    course_content = CourseContentGet.model_validate(query,from_attributes=True)

    try:
        await cache.set(cache_key, course_content.model_dump_json(), ttl=120)

    except Exception as e:
        raise e
    
    return course_content

## MR-based course-content messages removed (deprecated)

@student_router.get("/course-contents/{course_content_id}", response_model=CourseContentStudentGet)
def student_get_course_content(course_content_id: UUID | str, permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):

    course_contents_result = user_course_content_query(permissions.get_user_id_or_throw(),course_content_id,db)
 
    return course_member_course_content_result_mapper(course_contents_result, db, detailed=True)

@student_router.get("/course-contents", response_model=list[CourseContentStudentList])
def student_list_course_contents(permissions: Annotated[Principal, Depends(get_current_principal)], params: CourseContentStudentQuery = Depends(), db: Session = Depends(get_db)):

    query = user_course_content_list_query(permissions.get_user_id_or_throw(),db)

    course_contents_results = CourseContentStudentInterface.search(db,query,params).all()

    response_list: list[CourseContentStudentList] = []

    for course_contents_result in course_contents_results:
        response_list.append(course_member_course_content_result_mapper(course_contents_result, db))

    return response_list

@student_router.get("/courses", response_model=list[CourseStudentList])
async def student_list_courses(permissions: Annotated[Principal, Depends(get_current_principal)], params: CourseStudentQuery = Depends(), db: Session = Depends(get_db)):

    # TODO: query should be improved: course_contents for course_group_members shall be available. All ascendant sould be included afterwards, but in one query.

    courses = CourseStudentInterface.search(db,check_course_permissions(permissions,Course,"_student",db),params).all()

    response_list: list[CourseStudentList] = []

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

@student_router.get("/courses/{course_id}", response_model=CourseStudentGet)
async def student_get_course(course_id: UUID | str,permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):

    course = check_course_permissions(permissions,Course,"_student",db).filter(Course.id == course_id).first()

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