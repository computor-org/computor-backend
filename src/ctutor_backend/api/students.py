import json
import logging
from uuid import UUID
from typing import Annotated
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from fastapi import APIRouter, Depends
from ctutor_backend.api.exceptions import BadRequestException, InternalServerException, NotFoundException
from ctutor_backend.api.mappers import course_member_course_content_result_mapper
from ctutor_backend.api.messages import get_submission_mergerequest
from ctutor_backend.api.permissions import check_course_permissions
from ctutor_backend.api.queries import user_course_content_list_query, user_course_content_query
from ctutor_backend.interface.auth import GLPAuthConfig
from ctutor_backend.interface.course_contents import CourseContentGet
from ctutor_backend.interface.course_members import CourseMemberProperties
from ctutor_backend.interface.student_course_contents import CourseContentStudentInterface, CourseContentStudentList, CourseContentStudentQuery
from ctutor_backend.api.auth import HeaderAuthCredentials, get_auth_credentials, get_current_permissions
from ctutor_backend.database import get_db
from ctutor_backend.interface.permissions import Principal
from ctutor_backend.interface.student_courses import CourseStudentGet, CourseStudentInterface, CourseStudentList, CourseStudentQuery, CourseStudentRepository
from ctutor_backend.model.auth import User
from ctutor_backend.model.course import Course, CourseContent, CourseMember
from ctutor_backend.redis_cache import get_redis_client
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

async def student_course_content_messages_cached(course_content_id: str, user_id: str, permissions: Principal, cache: BaseCache, db: Session) -> tuple[CourseMemberProperties,str,str]:

    cache_key = f"{permissions.get_user_id_or_throw()}:course-contents:{course_content_id}"

    course_content = await cache.get(cache_key)

    if course_content != None:
        cached_obj = json.loads(course_content)

        course_member_properties = CourseMemberProperties.model_validate(cached_obj["properties"],from_attributes=True)
        course_content_id = cached_obj["course_content_id"]
        course_content_path = cached_obj["course_content_path"]

        return course_member_properties, course_content_id, course_content_path

    query = db.query(CourseMember.properties,CourseContent.id,CourseContent.path) \
        .select_from(CourseMember) \
            .join(Course,Course.id == CourseMember.course_id) \
                .join(CourseContent,CourseContent.course_id == Course.id) \
                    .join(User,User.id == CourseMember.user_id) \
                        .filter(
                            CourseContent.id == course_content_id,
                            CourseMember.user_id == user_id
                        ).first()
    
    if query == None:
        raise NotFoundException()

    course_member_properties = CourseMemberProperties(**query[0])
    course_content_id = str(query[1])
    course_content_path = str(query[2])

    try:
        await cache.set(cache_key, json.dumps({"properties":course_member_properties.model_dump(),"course_content_id": course_content_id,"course_content_path": course_content_path}), ttl=120)

    except Exception as e:
        raise e

    return course_member_properties, course_content_id, course_content_path

@student_router.get("/course-contents/{course_content_id}", response_model=CourseContentStudentList)
def student_get_course_content(course_content_id: UUID | str, permissions: Annotated[Principal, Depends(get_current_permissions)], db: Session = Depends(get_db)):

    course_contents_result = user_course_content_query(permissions.get_user_id_or_throw(),course_content_id,db)
 
    return course_member_course_content_result_mapper(course_contents_result, db)

@student_router.get("/course-contents", response_model=list[CourseContentStudentList])
def student_list_course_contents(permissions: Annotated[Principal, Depends(get_current_permissions)], params: CourseContentStudentQuery = Depends(), db: Session = Depends(get_db)):

    query = user_course_content_list_query(permissions.get_user_id_or_throw(),db)

    course_contents_results = CourseContentStudentInterface.search(db,query,params).all()

    response_list: list[CourseContentStudentList] = []

    for course_contents_result in course_contents_results:
        response_list.append(course_member_course_content_result_mapper(course_contents_result, db))

    return response_list

@student_router.get("/courses", response_model=list[CourseStudentList])
async def student_list_courses(permissions: Annotated[Principal, Depends(get_current_permissions)], params: CourseStudentQuery = Depends(), db: Session = Depends(get_db)):

    # TODO: query should be improved: course_contents for course_group_members shall be available. All ascendant sould be included afterwards, but in one query.

    courses = CourseStudentInterface.search(db,check_course_permissions(permissions,Course,"_student",db),params).all()

    response_list: list[CourseStudentList] = []

    for course in courses:

        response_list.append(CourseStudentList(
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
        ))

    return response_list

@student_router.get("/courses/{course_id}", response_model=CourseStudentGet)
async def student_get_course(course_id: UUID | str,permissions: Annotated[Principal, Depends(get_current_permissions)], db: Session = Depends(get_db)):

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

@student_router.get("/course-contents/{course_content_id}/messages", response_model=list[dict])
async def student_list_course_content_messages(
    course_content_id: UUID | str, 
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    auth_headers: Annotated[HeaderAuthCredentials,Depends(get_auth_credentials)],
    cache: Annotated[BaseCache, Depends(get_redis_client)], 
    db: Session = Depends(get_db)
):

    user_id = permissions.get_user_id_or_throw()

    course_member_properties, course_content_id, course_content_path = await student_course_content_messages_cached(course_content_id,user_id,permissions,cache,db)

    if auth_headers.type != GLPAuthConfig:
        raise BadRequestException(details="GitLab messages are restricted to GLPAT authenticated users")

    merge_request = await get_submission_mergerequest(auth_headers.credentials,user_id,course_member_properties.gitlab.full_path_submission,course_content_id,course_content_path)

    if merge_request == None:
        raise NotFoundException()

    notes = merge_request.notes.list()

    note_response = []
    for note in notes:
        note_response.append(note.asdict())

    return note_response

class CourseContentMessage(BaseModel):
    body: str

@student_router.post("/course-contents/{course_content_id}/messages", response_model=list[dict])
async def student_post_course_content_messages(
    course_content_id: UUID | str, 
    message: CourseContentMessage, 
    permissions: Annotated[Principal, Depends(get_current_permissions)],
    auth_headers: Annotated[HeaderAuthCredentials,Depends(get_auth_credentials)],
    cache: Annotated[BaseCache, Depends(get_redis_client)],
    db: Session = Depends(get_db)):

    if auth_headers.type != GLPAuthConfig:
        raise BadRequestException(details="GitLab messages are restricted to GLPAT authenticated users")

    user_id = permissions.get_user_id_or_throw()

    course_member_properties, course_content_id, course_content_path = await student_course_content_messages_cached(course_content_id,user_id,permissions,cache,db)

    merge_request = await get_submission_mergerequest(auth_headers.credentials,user_id,course_member_properties.gitlab.full_path_submission,course_content_id,course_content_path)

    if merge_request == None:
        raise NotFoundException()

    try:
        merge_request.notes.create({"body": message.body})
    except Exception as e:
        raise InternalServerException(detail=e.args)
    
    notes = merge_request.notes.list()

    note_response = []
    for note in notes:
        note_response.append(note.asdict())

    return note_response

@student_router.get("/repositories", response_model=list[str])
async def get_signup_init_data(permissions: Annotated[Principal, Depends(get_current_permissions)], db: Session = Depends(get_db)):

    # TODO: only gitlab is implemented yet
    properties = [q[0] for q in db.query(CourseMember.properties) \
        .join(User,User.id == CourseMember.user_id) \
            .filter(User.id == permissions.user_id,CourseMember.properties["gitlab"] != None).all()]

    repositories = []

    for p in properties:
        props = CourseMemberProperties(**p)
        repositories.append(f"{props.gitlab.url}/{props.gitlab.full_path}")

    return repositories


