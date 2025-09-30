import json
import logging
from uuid import UUID
from typing import Annotated
from pydantic import BaseModel
from sqlalchemy import case, desc
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from aiocache import SimpleMemoryCache
from ctutor_backend.database import get_db
from ctutor_backend.interface.course_content_types import CourseContentTypeList
from ctutor_backend.interface.course_member_comments import CourseMemberCommentList
from ctutor_backend.interface.course_members import CourseMemberGet, CourseMemberInterface, CourseMemberProperties, CourseMemberQuery
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import allowed_course_role_ids
from ctutor_backend.api.exceptions import BadRequestException, ForbiddenException, InternalServerException, NotFoundException
from ctutor_backend.api.mappers import course_member_course_content_result_mapper
from ctutor_backend.interface.student_courses import CourseStudentInterface, CourseStudentQuery
from ctutor_backend.interface.tutor_course_members import TutorCourseMemberCourseContent, TutorCourseMemberGet, TutorCourseMemberList
from ctutor_backend.interface.tutor_courses import CourseTutorGet, CourseTutorList, CourseTutorRepository
from ctutor_backend.model.auth import User
from ctutor_backend.model.course import Course, CourseContent, CourseContentKind, CourseMember, CourseMemberComment, SubmissionGroup, SubmissionGroupMember
from ctutor_backend.model.artifact import SubmissionArtifact, SubmissionGrade
from ctutor_backend.api.queries import course_course_member_list_query, course_member_course_content_list_query, course_member_course_content_query, latest_result_subquery, results_count_subquery, latest_grading_subquery
from ctutor_backend.interface.student_course_contents import (
    CourseContentStudentInterface,
    CourseContentStudentList,
    CourseContentStudentQuery,
    CourseContentStudentUpdate,
    ResultStudentList,
    SubmissionGroupStudentList,
    CourseContentStudentGet,
)
from ctutor_backend.interface.grading import GradingStatus
from ctutor_backend.interface.tutor_grading import TutorGradeCreate, TutorGradeResponse
from ctutor_backend.model.result import Result
from ctutor_backend.redis_cache import get_redis_client

logger = logging.getLogger(__name__)

_tutor_cache = SimpleMemoryCache()

_expiry_time_tutors = 3600 # in seconds

async def get_cached_data(course_id: str):
    # cached = await RedisCache.getInstance().get(f"{course_id}")
    cached = await _tutor_cache.get(f"{course_id}")

    if cached != None:
        return cached
    return None

async def set_cached_data(course_id: str, data: dict):
    # await RedisCache.getInstance().add(f"{course_id}", data, _expiry_time_students)
    await _tutor_cache.set(f"{course_id}", data, _expiry_time_tutors)

tutor_router = APIRouter()

@tutor_router.get("/course-members/{course_member_id}/course-contents/{course_content_id}", response_model=CourseContentStudentGet)
def tutor_get_course_contents(course_content_id: UUID | str, course_member_id: UUID | str, permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):
    
    if check_course_permissions(permissions,CourseMember,"_tutor",db).filter(CourseMember.id == course_member_id).first() == None:
        raise ForbiddenException()

    reader_user_id = permissions.get_user_id_or_throw()
    course_contents_result = course_member_course_content_query(course_member_id, course_content_id, db, reader_user_id=reader_user_id)

    return course_member_course_content_result_mapper(course_contents_result, db, detailed=True)

@tutor_router.get("/course-members/{course_member_id}/course-contents", response_model=list[CourseContentStudentList])
def tutor_list_course_contents(course_member_id: UUID | str, permissions: Annotated[Principal, Depends(get_current_principal)], params: CourseContentStudentQuery = Depends(), db: Session = Depends(get_db)):

    if check_course_permissions(permissions,CourseMember,"_tutor",db).filter(CourseMember.id == course_member_id).first() == None:
        raise ForbiddenException()

    reader_user_id = permissions.get_user_id_or_throw()
    query = course_member_course_content_list_query(course_member_id, db, reader_user_id=reader_user_id)

    course_contents_results = CourseContentStudentInterface.search(db,query,params).all()
 
    response_list: list[CourseContentStudentList] = []

    for course_contents_result in course_contents_results:
        response_list.append(course_member_course_content_result_mapper(course_contents_result, db))

    return response_list

@tutor_router.patch("/course-members/{course_member_id}/course-contents/{course_content_id}", response_model=TutorGradeResponse)
def tutor_update_course_contents(
    course_content_id: UUID | str,
    course_member_id: UUID | str,
    grade_data: TutorGradeCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    
    if check_course_permissions(permissions,CourseMember,"_tutor",db).filter(CourseMember.id == course_member_id).first() == None:
        raise ForbiddenException()

    # Create a new SubmissionGroupGrading entry before querying latest grading
    # 1) Resolve the student's course member and related submission group for this content
    student_cm = db.query(CourseMember).filter(CourseMember.id == course_member_id).first()
    if student_cm is None:
        raise NotFoundException()

    submission_group = (
        db.query(SubmissionGroup)
        .join(
            SubmissionGroupMember,
            SubmissionGroupMember.submission_group_id == SubmissionGroup.id,
        )
        .filter(
            SubmissionGroupMember.course_member_id == course_member_id,
            SubmissionGroup.course_content_id == course_content_id,
        )
        .first()
    )

    if submission_group is None:
        raise NotFoundException()

    # 2) Resolve the grader's course member (the current user in the same course)
    grader_cm = (
        db.query(CourseMember)
        .filter(
            CourseMember.user_id == permissions.get_user_id_or_throw(),
            CourseMember.course_id == student_cm.course_id,
        )
        .first()
    )
    if grader_cm is None:
        # Fallback safety: forbid if we cannot resolve grader identity in course
        raise ForbiddenException()

    # 3) Determine which artifact to grade
    if grade_data.artifact_id:
        # Specific artifact requested - verify it belongs to this submission group
        artifact_to_grade = (
            db.query(SubmissionArtifact)
            .filter(
                SubmissionArtifact.id == grade_data.artifact_id,
                SubmissionArtifact.submission_group_id == submission_group.id
            )
            .first()
        )
        if artifact_to_grade is None:
            raise NotFoundException(detail="Specified artifact not found or doesn't belong to this submission group")
    else:
        # Get the latest submission artifact for this submission group
        artifact_to_grade = (
            db.query(SubmissionArtifact)
            .filter(SubmissionArtifact.submission_group_id == submission_group.id)
            .order_by(SubmissionArtifact.created_at.desc())
            .first()
        )
        if artifact_to_grade is None:
            raise NotFoundException(detail="No submission artifact found for this submission group. Student must submit first.")

    # 4) Get grading status (now using GradingStatus enum directly)
    grading_status = grade_data.status if grade_data.status is not None else GradingStatus.NOT_REVIEWED

    # 5) Create a new artifact-based grade
    # Check if grading data is provided
    if grade_data.grade is not None or grade_data.status is not None:
        # Grade validation is already done by Pydantic Field validator (0.0 to 1.0)
        grade_value = grade_data.grade if grade_data.grade is not None else 0.0

        # Create the new grade for the artifact
        new_grading = SubmissionGrade(
            artifact_id=artifact_to_grade.id,
            graded_by_course_member_id=grader_cm.id,
            grade=grade_value,
            status=grading_status.value,
            comment=grade_data.feedback,
        )
        db.add(new_grading)
        db.commit()

        logger.info(f"Created grade for artifact {artifact_to_grade.id} by grader {grader_cm.id}")
        
    # 6) Return fresh data using shared mapper and latest grading subquery
    reader_user_id = permissions.get_user_id_or_throw()
    course_contents_result = course_member_course_content_query(course_member_id, course_content_id, db, reader_user_id=reader_user_id)

    # Map the result and enhance with graded artifact info
    response = course_member_course_content_result_mapper(course_contents_result, db)

    # Convert to TutorGradeResponse and add artifact info
    # Avoid model_dump() -> model_validate() round-trip to preserve UUID types
    grade_response = TutorGradeResponse.model_validate(response, from_attributes=True)
    grade_response.graded_artifact_id = artifact_to_grade.id
    grade_response.graded_artifact_info = {
        "id": str(artifact_to_grade.id),
        "created_at": artifact_to_grade.created_at.isoformat() if artifact_to_grade.created_at else None,
        "properties": artifact_to_grade.properties,
    }

    return grade_response

@tutor_router.get("/courses/{course_id}", response_model=CourseTutorGet)
async def tutor_get_courses(course_id: UUID | str, permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):

    course = check_course_permissions(permissions,Course,"_tutor",db).filter(Course.id == course_id).first()

    if course == None:
        raise NotFoundException()

    return CourseTutorGet(
                id=str(course.id),
                title=course.title,
                course_family_id=str(course.course_family_id) if course.course_family_id else None,
                organization_id=str(course.organization_id) if course.organization_id else None,
                path=course.path,
                repository=CourseTutorRepository(
                    provider_url=course.properties.get("gitlab", {}).get("url") if course.properties else None,
                    full_path_reference=f'{course.properties.get("gitlab", {}).get("full_path", "")}/reference' if course.properties and course.properties.get("gitlab", {}).get("full_path") else None
                ) if course.properties and course.properties.get("gitlab") else None
            )

@tutor_router.get("/courses", response_model=list[CourseTutorList])
def tutor_list_courses(permissions: Annotated[Principal, Depends(get_current_principal)], params: CourseStudentQuery = Depends(), db: Session = Depends(get_db)):

    query = check_course_permissions(permissions,Course,"_tutor",db)

    courses = CourseStudentInterface.search(db,query,params).all()

    response_list: list[CourseTutorList] = []

    for course in courses:
        response_list.append(CourseTutorList(
            id=str(course.id),
            title=course.title,
            course_family_id=str(course.course_family_id) if course.course_family_id else None,
            organization_id=str(course.organization_id) if course.organization_id else None,
            path=course.path,
            repository=CourseTutorRepository(
                provider_url=course.properties.get("gitlab", {}).get("url") if course.properties else None,
                full_path_reference=f'{course.properties.get("gitlab", {}).get("full_path", "")}/reference' if course.properties and course.properties.get("gitlab", {}).get("full_path") else None
            ) if course.properties and course.properties.get("gitlab") else None
        ))

    return response_list

# @tutor_router.get("/courses/{course_id}/current", response_model=CourseMemberGet)
# async def tutor_get_courses(course_id: UUID | str, permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):

#     course_member = check_course_permissions(permissions,CourseMember,"_tutor",db).filter(Course.id == course_id, CourseMember.user_id == permissions.get_user_id_or_throw()).first()

#     if course_member == None:
#         raise NotFoundException()

#     return CourseMemberGet(**course_member.__dict__)

@tutor_router.get("/course-members/{course_member_id}", response_model=TutorCourseMemberGet)
def tutor_get_course_members(course_member_id: UUID | str, permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):

    course_member = check_course_permissions(permissions,CourseMember,"_tutor",db).filter(CourseMember.id == course_member_id).first()

    reader_user_id = permissions.get_user_id_or_throw()
    course_contents_results = course_member_course_content_list_query(course_member_id, db, reader_user_id=reader_user_id).all()

    response_list: list[TutorCourseMemberCourseContent] = []

    for course_contents_result in course_contents_results:
        query = course_contents_result
        course_content = query[0]

        result = query[2]

        if result != None:
            # Get submit field from associated SubmissionArtifact
            submit = False
            if result.submission_artifact:
                submit = result.submission_artifact.submit
            status = result.status

            todo = True if submit == True and status == None else False
            if todo == True:
                response_list.append(TutorCourseMemberCourseContent(id=course_content.id,path=str(course_content.path)))

    tutor_course_member = TutorCourseMemberGet.model_validate(course_member,from_attributes=True)
    tutor_course_member.unreviewed_course_contents = response_list

    return tutor_course_member

@tutor_router.get("/course-members", response_model=list[TutorCourseMemberList])
def tutor_list_course_members(permissions: Annotated[Principal, Depends(get_current_principal)], params: CourseMemberQuery = Depends(), db: Session = Depends(get_db)):

    subquery = db.query(Course.id).select_from(User).filter(User.id == permissions.get_user_id_or_throw()) \
        .join(CourseMember, CourseMember.user_id == User.id) \
            .join(Course, Course.id == CourseMember.course_id) \
                .filter(CourseMember.course_role_id.in_((allowed_course_role_ids("_tutor")))).all()

    query = course_course_member_list_query(db)

    query = CourseMemberInterface.search(db,query,params)

    if permissions.is_admin != True:
        query = query.join(Course,Course.id == CourseMember.course_id).filter(Course.id.in_([r.id for r in subquery])).join(User,User.id == CourseMember.user_id).order_by(User.family_name).all()

    response_list: list[TutorCourseMemberList] = []

    for course_member, latest_result_date in query:
        tutor_course_member = TutorCourseMemberList.model_validate(course_member,from_attributes=True)
        tutor_course_member.unreviewed = True if latest_result_date != None else False
        response_list.append(tutor_course_member)

    return response_list

## MR-based course-content messages removed (deprecated)

## Comments routes moved to generic /course-member-comments
