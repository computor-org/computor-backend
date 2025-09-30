import json
import logging
from uuid import UUID
from typing import Annotated, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from fastapi import APIRouter, Depends
from gitlab import Gitlab
from ctutor_backend.api.exceptions import BadRequestException, InternalServerException, NotFoundException
from ctutor_backend.api.mappers import course_member_course_content_result_mapper
from ctutor_backend.permissions.core import check_course_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.api.queries import user_course_content_list_query, user_course_content_query
from ctutor_backend.interface.course_contents import CourseContentGet
from ctutor_backend.interface.course_members import CourseMemberProperties
from ctutor_backend.interface.student_course_contents import (
    CourseContentStudentInterface,
    CourseContentStudentList,
    CourseContentStudentQuery,
    CourseContentStudentGet,
)
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.database import get_db
from ctutor_backend.interface.student_courses import CourseStudentGet, CourseStudentInterface, CourseStudentList, CourseStudentQuery, CourseStudentRepository
from ctutor_backend.model.auth import User
from ctutor_backend.model.course import Course, CourseContent, CourseMember, SubmissionGroup, SubmissionGroupMember
from ctutor_backend.redis_cache import get_redis_client
from aiocache import BaseCache
student_router = APIRouter()
logger = logging.getLogger(__name__)

# Request/Response models for submit endpoint
class SubmitRequest(BaseModel):
    """Request model for creating a merge request submission."""
    branch_name: str = Field(..., description="The branch name to create merge request from")
    gitlab_token: str = Field(..., description="GitLab Personal Access Token for authentication")
    title: Optional[str] = Field(None, description="Optional title for the merge request")
    description: Optional[str] = Field(None, description="Optional description for the merge request")

class SubmitResponse(BaseModel):
    """Response model for merge request submission."""
    merge_request_id: int = Field(..., description="The ID of the created merge request")
    merge_request_iid: int = Field(..., description="The internal ID of the merge request")
    web_url: str = Field(..., description="The web URL of the merge request")
    source_branch: str = Field(..., description="The source branch of the merge request")
    target_branch: str = Field(..., description="The target branch of the merge request")
    title: str = Field(..., description="The title of the merge request")
    state: str = Field(..., description="The state of the merge request")

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

## MR-based course-content messages removed (deprecated)

@student_router.get("/repositories", response_model=list[str])
async def get_signup_init_data(permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):

    # TODO: only gitlab is implemented yet
    properties = [q[0] for q in db.query(CourseMember.properties) \
        .join(User,User.id == CourseMember.user_id) \
            .filter(User.id == permissions.user_id,CourseMember.properties["gitlab"] != None).all()]

    repositories = []

    for p in properties:
        props = CourseMemberProperties(**p)
        repositories.append(f"{props.gitlab.url}/{props.gitlab.full_path}")

    return repositories

# @student_router.post("/course-contents/{course_content_id}/submit", response_model=SubmitResponse)
# async def submit_assignment(
#     course_content_id: str,
#     submit_request: SubmitRequest,
#     permissions: Annotated[Principal, Depends(get_current_principal)],
#     db: Session = Depends(get_db),
#     cache: BaseCache = Depends(get_redis_client)
# ):
#     """
#     Create a merge request for submitting an assignment.
    
#     This endpoint creates a GitLab merge request from the specified branch
#     to the submission branch for the given course content.
#     """
    
#     user_id = permissions.get_user_id_or_throw()
    
#     # Get course content and validate access
#     course_content = await student_get_course_content_cached(
#         course_content_id, 
#         permissions, 
#         cache, 
#         db
#     )
    
#     # Find the submission group for this course content that the user belongs to
#     submission_group = db.query(SubmissionGroup).join(
#         SubmissionGroupMember,
#         SubmissionGroupMember.submission_group_id == SubmissionGroup.id
#     ).join(
#         CourseMember,
#         CourseMember.id == SubmissionGroupMember.course_member_id
#     ).filter(
#         SubmissionGroup.course_content_id == course_content_id,
#         CourseMember.user_id == user_id
#     ).first()
    
#     if not submission_group:
#         raise NotFoundException(detail="No submission group found for this assignment")
    
#     # Check if submission group has GitLab configuration in properties
#     if not submission_group.properties or 'gitlab' not in submission_group.properties:
#         raise BadRequestException(detail="GitLab not configured for this submission group")

    
#     # First, check if there's a result for this submission group
#     from ctutor_backend.model.result import Result
    
#     # Find the last result for this submission group
#     last_result = db.query(Result).filter(
#         Result.submission_group_id == submission_group.id
#     ).order_by(Result.created_at.desc()).first()
    
#     if not last_result:
#         raise BadRequestException(detail="No test results found. You must run tests before submitting.")
    
#     gitlab_config = submission_group.properties.get('gitlab', {})
    
#     # Extract GitLab URL and namespace path from submission group properties
#     gitlab_url = gitlab_config.get('url')
#     namespace_path = gitlab_config.get('full_path')
    
#     if not gitlab_url:
#         raise BadRequestException(detail="GitLab URL not configured in submission group")
    
#     if not namespace_path:
#         raise BadRequestException(detail="GitLab namespace path not configured in submission group")
    
#     # Initialize GitLab client with the token from request
#     gitlab = Gitlab(url=gitlab_url, private_token=submit_request.gitlab_token)

#     try:
#         projects = gitlab.projects.list(
#             search=namespace_path,  # Search by project name
#             search_namespaces=True
#         )
        
#         # Filter to find exact match
#         matching_projects = [p for p in projects if p.path_with_namespace == namespace_path]
        
#         if len(matching_projects) == 0:
#             raise NotFoundException(detail=f"Repository not found at path: {namespace_path}")
#         elif len(matching_projects) > 1:
#             raise InternalServerException(detail="Multiple repositories found with same path")
        
#         project = matching_projects[0]
#     except Exception as search_error:
#         logger.error(f"Failed to find GitLab project at {namespace_path}: {search_error}")
#         raise NotFoundException(detail=f"Failed to find repository: {namespace_path}")
    
#     # Prepare merge request data
#     mr_title = submit_request.title or f"Submission: {course_content.path}"
#     mr_description = submit_request.description or f"Assignment submission for {course_content.title}"
    
#     # The target branch is typically the submission branch for the assignment
#     target_branch = f"submission/{course_content.path}"
    
#     merge_request = None
#     merge_request_exists = False
    
#     try:
#         # First check if a merge request already exists from this branch
#         existing_mrs = project.mergerequests.list(
#             source_branch=submit_request.branch_name,
#             state='opened'  # Only look for open merge requests
#         )
        
#         if existing_mrs:
#             # Merge request already exists, use the existing one
#             merge_request = existing_mrs[0]
#             merge_request_exists = True
#             logger.info(f"Using existing merge request {merge_request.iid} for branch {submit_request.branch_name}")
#         else:
#             # Check if target branch exists, if not use 'main' or 'master'
#             branches = project.branches.list()
#             branch_names = [b.name for b in branches]
            
#             if target_branch not in branch_names:
#                 # Fallback to main or master
#                 if 'main' in branch_names:
#                     target_branch = 'main'
#                 elif 'master' in branch_names:
#                     target_branch = 'master'
#                 else:
#                     # Use the default branch
#                     target_branch = project.default_branch
            
#             # Create new merge request
#             merge_request = project.mergerequests.create({
#                 'source_branch': submit_request.branch_name,
#                 'target_branch': target_branch,
#                 'title': mr_title,
#                 'description': mr_description,
#                 'remove_source_branch_after_merge': False,  # Keep student's branch
#                 'squash': False  # Preserve commit history
#             })
#             logger.info(f"Created new merge request {merge_request.iid} for branch {submit_request.branch_name}")
        
#         # Update the last result to mark it as submitted
#         last_result.submit = True
#         db.commit()
#         logger.info(f"Marked result {last_result.id} as submitted")
        
#         # Cache the merge request for quick retrieval
#         cache_key = f"{user_id}:merge_request:{course_content_id}"
#         await cache.set(cache_key, json.dumps(merge_request.asdict()), ttl=1800)
        
#         # Return the response
#         return SubmitResponse(
#             merge_request_id=merge_request.id,
#             merge_request_iid=merge_request.iid,
#             web_url=merge_request.web_url,
#             source_branch=merge_request.source_branch,
#             target_branch=merge_request.target_branch,
#             title=merge_request.title,
#             state=merge_request.state
#         )
        
#     except Exception as e:
#         logger.error(f"Failed to handle merge request: {e}")
#         # Roll back the submit flag if merge request handling failed
#         db.rollback()
        
#         # Check if it's a specific GitLab error
#         if "already exists" in str(e).lower() and not merge_request_exists:
#             raise BadRequestException(detail="A merge request from this branch already exists")
#         elif "not found" in str(e).lower():
#             raise BadRequestException(detail=f"Branch '{submit_request.branch_name}' not found in repository")
#         else:
#             raise InternalServerException(detail=f"Failed to handle merge request: {str(e)}")
