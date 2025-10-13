from collections import defaultdict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Annotated, Optional, List, Dict, Any
from fastapi import BackgroundTasks, Depends, APIRouter, File, UploadFile, HTTPException, status
from datetime import datetime, timezone
import logging

from computor_backend.business_logic.crud import get_entity_by_id as get_id_db
from computor_backend.api.exceptions import BadRequestException, NotFoundException, NotImplementedException
from computor_backend.api.filesystem import mirror_entity_to_filesystem
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import check_admin, check_course_permissions, get_permitted_course_ids
from computor_backend.permissions.principal import Principal

from computor_backend.api.utils import get_course_id_from_url, sync_dependent_items
from computor_backend.database import get_db
from computor_types.course_groups import CourseGroupCreate
from computor_types.deployments import ComputorDeploymentConfig, CourseConfig, CourseFamilyConfig, GitLabConfig, OrganizationConfig
from computor_types.organizations import OrganizationProperties
from computor_types.student_profile import StudentProfileCreate
from computor_types.tokens import decrypt_api_key
from computor_types.users import UserCreate, UserGet, UserTypeEnum
from computor_types.system import (
    StudentCreate, ReleaseStudentsCreate, TUGStudentExport, ReleaseCourseCreate,
    ReleaseCourseContentCreate, StatusQuery, CourseReleaseUpdate, GitLabCredentials,
    OrganizationTaskRequest, CourseFamilyTaskRequest, CourseTaskRequest, TaskResponse,
    PendingChange, PendingChangesResponse, GenerateTemplateRequest, GenerateTemplateResponse,
    BulkAssignExamplesRequest,
    GenerateAssignmentsRequest, GenerateAssignmentsResponse,
)
from computor_types.lecturer_deployments import ReleaseValidationError
from computor_backend.model.course import Course, CourseContent, CourseContentType, CourseFamily, CourseGroup, CourseMember
from computor_backend.model.organization import Organization  
from computor_backend.model.auth import User, StudentProfile
from computor_backend.model.example import Example
from computor_backend.redis_cache import get_redis_client
from aiocache import BaseCache
from computor_backend.tasks import get_task_executor, TaskSubmission
from computor_backend.business_logic.release_validation import (
    validate_course_for_release,
    validate_course_contents_for_release
)

system_router = APIRouter()
logger = logging.getLogger(__name__)

# def get_computor_deployment_from_course_id_db(course_id: UUID | str, db: Session) -> ComputorDeploymentConfig: # TODO: REFACTORING

#     query = db.query(Course,CourseFamily,Organization) \
#                 .join(CourseFamily,CourseFamily.id == Course.course_family_id) \
#                     .join(Organization, Organization.id == Course.organization_id) \
#             .filter(Course.id == course_id).first()

#     course: Course = query[0]
#     course_family: CourseFamily = query[1]
#     organization: Organization = query[2]

#     deployment = ComputorDeploymentConfig(
#         organization=OrganizationConfig(
#             name=organization.title,
#             path=organization.path.path,
#             description=organization.description,
#             settings=organization.properties
#         ),
#         courseFamily=CourseFamilyConfig(
#             name=course_family.title,
#             path=course_family.path.path,
#             description=course_family.description,
#             settings=course_family.properties
#         ),
#         course=CourseConfig(
#             name=course.title,
#             path=course.path.path,
#             description=course.description,
#             settings=course.properties
#         )
#     )

#     properties = OrganizationProperties(**organization.properties)

#     if properties.gitlab != None:

#         deployment.organization.gitlab = GitLabConfig(
#             url=properties.gitlab.url,
#             full_path=properties.gitlab.full_path,
#             token=decrypt_api_key(properties.gitlab.token),
#             parent=properties.gitlab.parent
#         )

#     else:
#         raise NotImplementedError()

#     return deployment

# @system_router.post("/release/students", response_model=dict)
# async def create_student(payload: ReleaseStudentsCreate, permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):

#     course_id = payload.course_id
#     students = payload.students

#     if check_course_permissions(permissions,Course,"_maintainer",db).filter(Course.id == course_id).first() == None:
#        raise NotFoundException()

#     for p in students:
#       if p.course_group_id != None:
#         if db.query(CourseGroup.id).filter(CourseGroup.id == p.course_group_id).count() != 1:
#             raise BadRequestException(detail=f"CourseGroup with id {p.course_group_id} does not exist")
#       elif p.course_group_title != None:
#         course_group_id = db.query(CourseGroup.id).filter(CourseGroup.course_id == course_id,CourseGroup.title == p.course_group_title).scalar()

#         if course_group_id == None:
#           raise BadRequestException(detail=f"CourseGroup with id {course_group_id} does not exist")

#         p.course_group_id = course_group_id
#       else:
#         if p.role in ["_tutor","_maintainer","_owner"]:
#           p.course_group_id = None
#         else:
#           raise BadRequestException(detail=f"Student must be in a course group")   

#       if p.user == None:

#         if p.user_id == None:
#            raise BadRequestException(detail=f"User and user id not in payload")

#         user = db.query(User).filter(User.id == p.user_id).first()

#         if user == None:
#             raise BadRequestException(detail=f"User with id {p.user_id} does not exist")

#         p.user = user

#     deployment = get_computor_deployment_from_course_id_db(course_id, db)

#     # Use Temporal task executor
#     task_executor = get_task_executor()
    
#     task_submission = TaskSubmission(
#         task_name="release_students",
#         parameters={
#             "deployment": deployment.model_dump(),
#             "release_data": ReleaseStudentsCreate(
#                 students=students,
#                 course_id=course_id
#             ).model_dump()
#         },
#         queue="computor-tasks"
#     )
    
#     task_id = await task_executor.submit_task(task_submission)
    
#     return {"task_id": task_id}
  
# @system_router.post("/release/students/export", response_model=list[TUGStudentExport])
# async def create_student_from_export(permissions: Annotated[Principal, Depends(get_current_principal)], course_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):

#     if check_course_permissions(permissions,Course,"_maintainer",db).filter(Course.id == course_id).first() == None and check_admin(permissions) == False:
#       raise NotFoundException()

#     # course_path_ = str(db.query(Course.path).filter(Course.id == course_id).scalar())

#     # course_path_splitted = course_path_.split(".")

#     # if len(course_path_splitted) > 1:
#     #   course_path = ".".join(course_path_splitted[1:])
#     # else:
#     #   course_path = course_path_

#     import pandas as pd
#     from io import StringIO

#     content = await file.read()

#     csv_string = StringIO(content.decode("utf-8"))

#     df = pd.read_csv(csv_string)

#     students: list[TUGStudentExport] = []
#     for index, row in df.iterrows():
#       student = TUGStudentExport(
#          course_group_title = str(row["Gruppe"]).rstrip().lstrip(),
#          family_name = str(row["Familienname"]).rstrip().lstrip(),
#          given_name = str(row["Vorname"]).rstrip().lstrip(),
#          matriculation_number = str(row["Matrikelnummer"]).rstrip().lstrip(),
#          created_at = str(row["Anmeldedatum"]).rstrip().lstrip(),
#          email = str(row["E-Mail"]).rstrip().lstrip())

#       #if student.course_group_title.lower().endswith(course_path):
#       students.append(student)

#     course_groups = defaultdict(list)
#     for student in students:
#       course_groups[student.course_group_title].append(student)
    
#     course_member_create_tasks: list[StudentCreate] = []

#     for course_group_title, group in course_groups.items():

#       course_group_db = db.query(CourseGroup).filter(CourseGroup.course_id == course_id, CourseGroup.title == course_group_title).first()

#       if course_group_db == None:
#         course_group_create = CourseGroupCreate(
#           title=course_group_title,
#           course_id=course_id
#         )

#         course_group_db = CourseGroup(**course_group_create.model_dump())

#         db.add(course_group_db)
#         db.commit()
#         db.refresh(course_group_db)
      
#       for student in group:
#         student_profiles_count = (
#           db.query(User.id, func.count(StudentProfile.id).label("profile_count"))
#           .outerjoin(StudentProfile, StudentProfile.user_id == User.id)
#           .group_by(User.id)
#           .subquery()
#         )
        
#         query = db.query(User,StudentProfile).select_from(User) \
#           .outerjoin(StudentProfile,StudentProfile.user_id == User.id) \
#             .outerjoin(student_profiles_count, student_profiles_count.c.id == User.id) \
#               .filter(
#                 or_(
#                     and_(StudentProfile.student_email == student.email,StudentProfile.student_id == student.matriculation_number),
#                     and_(User.email == student.email, student_profiles_count.c.profile_count == 0))).first()

#         user_db = query[0] if query != None else None
#         student_profile_db = query[1] if query != None else None

#         if user_db == None:

#           user_create = UserCreate(
#             given_name=student.given_name,
#             family_name=student.family_name,
#             user_type=UserTypeEnum.user,
#             email=student.email
#           )
          
#           user_db = User(**user_create.model_dump())

#           db.add(user_db)
#           db.commit()
#           db.refresh(user_db)

#           user_id = user_db.id
#         else:
#           user_id = query[0].id
        
#         if student_profile_db == None:
#           student_profile = StudentProfileCreate(
#             student_id=student.matriculation_number,
#             student_email=student.email,
#             user_id = user_id
#           )

#           student_profile_db = StudentProfile(**student_profile.model_dump())

#           db.add(student_profile_db)
#           db.commit()
#           db.refresh(student_profile_db)

#         course_member_db = db.query(CourseMember).filter(CourseMember.course_id == course_id, CourseMember.user_id == user_db.id).first()

#         if course_member_db == None: 
#           course_member_create = CourseMemberCreate(
#             user_id=user_db.id,
#             course_id=course_id,
#             course_group_id=course_group_db.id,
#             course_role_id="_student"
#           )

#           course_member_db = CourseMember(**course_member_create.model_dump())

#           db.add(course_member_db)
#           db.commit()
#           db.refresh(course_member_db)

#           CourseMemberInterface.post_create(course_member_db,db)
#         else:
#           if course_member_db.course_group_id != course_group_db.id:
#             course_member_db.course_group_id = course_group_db.id

#             db.commit()
#             db.refresh(course_member_db)

#         props = CourseMemberProperties(**course_member_db.properties) if course_member_db.properties != None else None

#         if props == None or props != None and props.gitlab == None:
#            course_member_create_tasks.append(StudentCreate(
#               user_id=str(user_db.id),
#               user=UserGet(**user_db.__dict__),
#               course_group_id=str(course_group_db.id),
#               role="_student"
#            ))

#     if len(course_member_create_tasks) > 0:
#       deployment = get_computor_deployment_from_course_id_db(course_id, db)

#       raise NotImplementedException()
#       # async with get_prefect_client() as client:

#       #   deployment_response = await client.read_deployment_by_name("release-student/system")

#       #   try:
#       #     flow_run = await client.create_flow_run_from_deployment(
#       #       deployment_id=deployment_response.id,
#       #       parameters={
#       #         "deployment": deployment.model_dump(),
#       #         "payload": ReleaseStudentsCreate(
#       #           students=course_member_create_tasks,
#       #           course_id=course_id
#       #         ).model_dump()
#       #       }
#       #     )
#       #     print(f"Started flow_run {flow_run}")

#       #   except Exception as e:
#       #     raise BadRequestException()

#     return students

# async def create_course_client(course_id: str | None, deployment: ComputorDeploymentConfig, release_dir: str | None = None, ascendants: bool = False, descendants: bool = False, release_dir_list: list[str] = []):
#     # Use Temporal task executor
#     task_executor = get_task_executor()
    
#     task_submission = TaskSubmission(
#         task_name="release_course",
#         parameters={
#             "deployment": deployment.model_dump(),
#             "release_dir": release_dir,
#             "ascendants": ascendants if ascendants else False,
#             "descendants": descendants if descendants else False,
#             "release_dir_list": release_dir_list
#         },
#         queue="computor-tasks"
#     )
    
#     task_id = await task_executor.submit_task(task_submission)
    
#     return {"task_id": task_id}

# @system_router.post("/release/courses", response_model=dict)
# async def release_course(payload: ReleaseCourseCreate, permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):
#     if payload.course_id != None:
#       course_id = payload.course_id
#     elif payload.gitlab_url != None:
#       course_id = get_course_id_from_url(payload.gitlab_url,db)
#     elif payload.deployment != None:
#       if check_admin(permissions) == False:
#         raise NotFoundException()
#       # TODO: course_id = None is wrong
#       return await create_course_client(None,payload.deployment,None,None,payload.descendants)
#     else:
#       raise BadRequestException()

#     if check_course_permissions(permissions,Course,"_maintainer",db).filter(Course.id == course_id).first() == None:
#       raise NotFoundException()

#     return await create_course_client(course_id,get_computor_deployment_from_course_id_db(course_id, db),None,None,payload.descendants)

# @system_router.post("/release/course-contents", response_model=dict)
# async def release_course_content(payload: ReleaseCourseContentCreate, permissions: Annotated[Principal, Depends(get_current_principal)], db: Session = Depends(get_db)):

#     if payload.course_id != None:
#       course_id = payload.course_id

#     elif payload.gitlab_url != None:
#       course_id = get_course_id_from_url(payload.gitlab_url,db)

#     else:
#       raise BadRequestException()

#     if check_course_permissions(permissions,Course,"_maintainer",db).filter(Course.id == course_id).first() == None:
#       raise NotFoundException()

#     return await create_course_client(course_id, get_computor_deployment_from_course_id_db(course_id, db), payload.release_dir, payload.ascendants, payload.descendants,payload.release_dir_list)

# @system_router.get("/status/{task_id}", response_model=dict)
# async def system_job_status(task_id: UUID | str, permissions: Annotated[Principal, Depends(get_current_principal)], params: StatusQuery = Depends()):
#     # Use Temporal task executor
#     task_executor = get_task_executor()
    
#     # Check permissions
#     if not permissions.is_admin:
#         # For non-admin users, we need to verify they have access to this task
#         # This is a simplified version - in production you might want to store
#         # task metadata in Redis or database to verify ownership
#         if params.course_id:
#             with next(get_db()) as db:
#                 if params.course_id not in get_permitted_course_ids(permissions, "_lecturer", db):
#                     raise NotFoundException()
    
#     try:
#         # Get task status
#         task_info = await task_executor.get_task_status(str(task_id))
        
#         # Map status
#         if task_info.status == 'QUEUED':
#             status = 'PENDING'
#             message = 'Task is queued for processing'
#         elif task_info.status == 'STARTED':
#             status = 'RUNNING'
#             message = task_info.progress.get('status', 'In progress') if task_info.progress else 'In progress'
#         elif task_info.status == 'FINISHED':
#             status = 'COMPLETED'
#             message = 'Task completed successfully'
#         elif task_info.status == 'FAILED':
#             status = 'FAILED'
#             message = task_info.error or 'Task failed'
#         else:
#             status = task_info.status
#             message = None
        
#         response_dict = {"status": status}
#         if message:
#             response_dict["message"] = message
        
#         # Include result data for completed tasks
#         if task_info.status == 'FINISHED':
#             try:
#                 task_result = await task_executor.get_task_result(str(task_id))
#                 if task_result.result:
#                     response_dict["result"] = task_result.result
#             except Exception:
#                 pass
        
#         return response_dict
        
#     except Exception as e:
#         # Task not found
#         return {
#             "status": "NOT_FOUND",
#             "message": f"Task not found: {str(e)}"
#         }

# SYSTEM RESPONSE ROUTES - NOT CALLABLE FROM NON-SYSTEM CLIENTS

# @system_router.patch("/release/courses/{course_id}/callback", response_model=bool)
# async def release_course_response(
#    background_tasks: BackgroundTasks, 
#    course_id: UUID | str, 
#    course_release_update: CourseReleaseUpdate, 
#    permissions: Annotated[Principal, Depends(get_current_principal)],
#    cache: Annotated[BaseCache, Depends(get_redis_client)],
#    db: Session = Depends(get_db)):

#     if await get_id_db(permissions,db,course_id,CourseInterface,"update") == None:
#        raise NotFoundException()

#     ## UPDATE EXISTING COURSE

#     course_db = db.query(Course).filter(Course.id == course_id).first()

#     if course_db == None:
#         raise NotFoundException()
#     try:

#       if course_release_update.course != None:
#         course_update = course_release_update.course

#         for key in course_update.model_fields_set:
#           setattr(course_db, key, getattr(course_update,key))

#       course_content_types = course_release_update.course_content_types

#       content_by_kind = defaultdict(list)

#       for content in course_content_types:
#         kind_id = content.course_content_kind_id
#         content_by_kind[kind_id].append(content)

#       for kind, contents in content_by_kind.items():
#         sync_dependent_items(
#           dependents=[("course_id", course_id),("course_content_kind_id", kind)],
#           dependent_items=contents,
#           dependent_item_type=CourseContentType,
#           foreign_key="slug",
#           db=db)

#       db.commit()

#       await cache.clear(Course.__tablename__)
#       await cache.clear(CourseContent.__tablename__)
#       await cache.clear(CourseContentType.__tablename__)
#       await cache.clear(CourseGroup.__tablename__)

#       async def event_wrapper():
#           try:
#               await mirror_entity_to_filesystem(course_id,CourseInterface,db)
#           except Exception as e:
#               print(e)

#       background_tasks.add_task(event_wrapper)

#       return True

#     except Exception as e:
#        db.rollback()
#        print(e.args)
#        print(e.with_traceback())
#        raise BadRequestException(e.args)

# HIERARCHY TASK ENDPOINTS

def convert_to_gitlab_config(gitlab: GitLabCredentials, parent_group_id: Optional[int], path: str) -> dict:
    """Convert GitLab credentials to config format."""
    config = {
        "url": gitlab.gitlab_url,
        "token": gitlab.gitlab_token,
        "path": path
    }
    if parent_group_id is not None:
        config["parent"] = parent_group_id
    return config

@system_router.post("/deploy/organizations", response_model=TaskResponse)
async def create_organization_async(
    request: OrganizationTaskRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """Create an organization asynchronously using Temporal workflows."""
    
    try:
        # Check permissions
        if not permissions.is_admin:
            raise NotFoundException("Insufficient permissions")
        
        # Convert to organization config format
        org_config = {
            "name": request.organization.get("title", ""),
            "path": request.organization.get("path", ""),
            "description": request.organization.get("description", ""),
            "gitlab": convert_to_gitlab_config(
                request.gitlab,
                request.parent_group_id,
                request.organization.get("path", "")
            )
        }
        
        # Submit task using Temporal
        task_executor = get_task_executor()
        task_submission = TaskSubmission(
            task_name="create_organization",
            parameters={
                "org_config": org_config,
                "gitlab_url": request.gitlab.gitlab_url,
                "gitlab_token": request.gitlab.gitlab_token,
                "user_id": permissions.user_id
            },
            queue="computor-tasks"
        )
        
        task_id = await task_executor.submit_task(task_submission)
        
        return TaskResponse(
            task_id=task_id,
            status="submitted",
            message="Organization creation task submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting organization creation task: {e}")
        raise BadRequestException(f"Failed to submit organization creation task: {str(e)}")

@system_router.post("/deploy/course-families", response_model=TaskResponse)
async def create_course_family_async(
    request: CourseFamilyTaskRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """Create a course family asynchronously using Temporal workflows."""
    
    try:
        # Check permissions
        if not permissions.is_admin:
            raise NotFoundException("Insufficient permissions")
        
        # Validate parent organization exists
        organization = db.query(Organization).filter(Organization.id == request.organization_id).first()
        if not organization:
            raise NotFoundException(f"Organization with ID {request.organization_id} not found")
        
        # Check if organization has GitLab integration
        parent_gitlab_config = organization.properties.get("gitlab", {})
        has_gitlab = bool(parent_gitlab_config.get("group_id"))
        
        # Convert to course family config format
        family_config = {
            "name": request.course_family.get("title", ""),
            "path": request.course_family.get("path", ""),
            "description": request.course_family.get("description", ""),
            "organization_id": request.organization_id,
            "has_gitlab": has_gitlab
        }
        
        # Submit task using Temporal
        # The task will fetch GitLab credentials from the organization
        task_executor = get_task_executor()
        task_submission = TaskSubmission(
            task_name="create_course_family",
            parameters={
                "family_config": family_config,
                "organization_id": request.organization_id,
                "user_id": permissions.user_id
            },
            queue="computor-tasks"
        )
        
        task_id = await task_executor.submit_task(task_submission)
        
        return TaskResponse(
            task_id=task_id,
            status="submitted",
            message="Course family creation task submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting course family creation task: {e}")
        raise BadRequestException(f"Failed to submit course family creation task: {str(e)}")

@system_router.post("/deploy/courses", response_model=TaskResponse)
async def create_course_async(
    request: CourseTaskRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """Create a course asynchronously using Temporal workflows."""
    
    try:
        # Check permissions
        if not permissions.is_admin:
            raise NotFoundException("Insufficient permissions")
        
        # Validate parent course family exists
        course_family = db.query(CourseFamily).filter(CourseFamily.id == request.course_family_id).first()
        if not course_family:
            raise NotFoundException(f"Course family with ID {request.course_family_id} not found")
        
        # Check if course family has GitLab integration
        parent_gitlab_config = course_family.properties.get("gitlab", {})
        has_gitlab = bool(parent_gitlab_config.get("group_id"))
        
        # Convert to course config format
        course_config = {
            "name": request.course.get("title", ""),
            "path": request.course.get("path", ""),
            "description": request.course.get("description", ""),
            "course_family_id": request.course_family_id,
            "has_gitlab": has_gitlab
        }
        
        # Submit task using Temporal
        # The task will fetch GitLab credentials from the course family
        task_executor = get_task_executor()
        task_submission = TaskSubmission(
            task_name="create_course",
            parameters={
                "course_config": course_config,
                "course_family_id": request.course_family_id,
                "user_id": permissions.user_id
            },
            queue="computor-tasks"
        )
        
        task_id = await task_executor.submit_task(task_submission)
        
        return TaskResponse(
            task_id=task_id,
            status="submitted",
            message="Course creation task submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error submitting course creation task: {e}")
        raise BadRequestException(f"Failed to submit course creation task: {str(e)}")

# GitLab Release System Endpoints

# @system_router.get(
#     "/courses/{course_id}/pending-changes",
#     response_model=PendingChangesResponse
# )
# async def get_pending_changes(
#     course_id: str,
#     permissions: Annotated[Principal, Depends(get_current_principal)],
#     db: Session = Depends(get_db)
# ):
#     """
#     Get pending changes that will be applied in the next template generation.
    
#     Compares current assignments with the last release to show what will change.
#     """
#     # Check permissions
#     if check_course_permissions(permissions, Course, "_lecturer", db).filter(Course.id == course_id).first() is None:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to view this course"
#         )
    
#     # Verify course exists
#     course = db.query(Course).filter(Course.id == course_id).first()
#     if not course:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Course {course_id} not found"
#         )
    
#     # Get all course contents
#     contents = db.query(CourseContent).filter(
#         CourseContent.course_id == course_id
#     ).all()
    
#     changes = []
    
#     for content in contents:
#         # Determine change type based on deployment status
#         if content.deployment_status == "pending_release":
#             if content.example_id:
#                 # Check if it's new or update
#                 if content.deployed_at is None:
#                     change_type = "new"
#                 else:
#                     change_type = "update"
                
#                 # Get example details
#                 example = db.query(Example).filter(
#                     Example.id == content.example_id
#                 ).first()
                
#                 change = PendingChange(
#                     type=change_type,
#                     content_id=str(content.id),
#                     path=str(content.path),
#                     title=content.title,
#                     example_name=example.title if example else None,
#                     example_id=str(content.example_id),
#                     to_version=content.example_version
#                 )
                
#                 # For updates, try to get the from_version
#                 if change_type == "update":
#                     change.from_version = "unknown"  # TODO: Track previous version
                
#                 changes.append(change)
#             else:
#                 # Example was removed
#                 if content.deployed_at is not None:
#                     changes.append(PendingChange(
#                         type="remove",
#                         content_id=str(content.id),
#                         path=str(content.path),
#                         title=content.title
#                     ))
    
#     # Get last release info from course properties
#     last_release = None
#     if course.properties and "last_template_release" in course.properties:
#         last_release = course.properties["last_template_release"]
    
#     return PendingChangesResponse(
#         total_changes=len(changes),
#         changes=changes,
#         last_release=last_release
#     )

@system_router.post(
    "/courses/{course_id}/generate-student-template",
    response_model=GenerateTemplateResponse
)
async def generate_student_template(
    course_id: str,
    request: GenerateTemplateRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Generate student template from assigned examples (Git operations).
    
    This is step 2 of the two-step process. It triggers a Temporal workflow
    that will:
    1. Download examples from MinIO based on CourseContent assignments
    2. Process them according to meta.yaml rules
    3. Generate the student-template repository
    4. Commit and push the changes
    """
    # Check permissions
    if check_course_permissions(permissions, Course, "_lecturer", db).filter(Course.id == course_id).first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to generate template for this course"
        )
    
    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course {course_id} not found"
        )
    
    # Get student-template and assignments URLs
    student_template_url = None
    assignments_url = None
    
    # First check if course has GitLab properties
    if course.properties and "gitlab" in course.properties:
        course_gitlab = course.properties["gitlab"]
        
        # Option 1: Direct URLs stored (backward compatibility)
        if "student_template_url" in course_gitlab:
            student_template_url = course_gitlab["student_template_url"]
        if "assignments_url" in course_gitlab:
            assignments_url = course_gitlab["assignments_url"]
        
        # Option 2: Construct from course's full_path  
        if "full_path" in course_gitlab and (not student_template_url or not assignments_url):
            # Get GitLab URL from organization
            if not course.course_family_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Course missing course family reference"
                )
            
            family = db.query(CourseFamily).filter(CourseFamily.id == course.course_family_id).first()
            if not family or not family.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Course family or organization not found"
                )
            
            org = db.query(Organization).filter(Organization.id == family.organization_id).first()
            if not org or not org.properties or "gitlab" not in org.properties:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization missing GitLab configuration"
                )
            
            gitlab_url = org.properties["gitlab"].get("url")
            if not gitlab_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization missing GitLab URL"
                )
            
            # Construct URLs: {gitlab_url}/{course_full_path}/student-template and assignments
            if not student_template_url:
                student_template_url = f"{gitlab_url}/{course_gitlab['full_path']}/student-template"
            if not assignments_url:
                assignments_url = f"{gitlab_url}/{course_gitlab['full_path']}/assignments"
    
    if not student_template_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to determine student-template repository URL. Course needs GitLab configuration with either 'student_template_url' or 'full_path'."
        )
    
    # PRE-FLIGHT VALIDATION: Check that selected assignments have valid examples
    # Extract selection parameters from release if available
    course_content_ids = None
    parent_id = None
    include_descendants = True
    all_flag = False

    if request.release:
        course_content_ids = request.release.course_content_ids
        parent_id = request.release.parent_id
        include_descendants = request.release.include_descendants if hasattr(request.release, 'include_descendants') else True
        all_flag = getattr(request.release, 'all', False)

    is_valid, validation_errors = validate_course_for_release(
        course_id=course_id,
        db=db,
        force_redeploy=request.force_redeploy,
        course_content_ids=course_content_ids,
        parent_id=parent_id,
        include_descendants=include_descendants,
        all_flag=all_flag
    )

    if not is_valid:
        logger.error(
            f"Release validation failed for course {course_id}: "
            f"{len(validation_errors)} issues found"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ReleaseValidationError(
                error="Cannot release course: Some assignments are missing examples or have invalid deployments",
                validation_errors=validation_errors,
                total_issues=len(validation_errors)
            ).model_dump()
        )

    logger.info(f"Pre-flight validation passed for course {course_id}")

    # Count contents to process - check for deployments instead of example_id
    from computor_backend.model.deployment import CourseContentDeployment

    contents_with_examples = db.query(func.count(CourseContent.id)).filter(
        and_(
            CourseContent.course_id == course_id,
            CourseContent.id.in_(
                db.query(CourseContentDeployment.course_content_id)
                .filter(CourseContentDeployment.deployment_status == 'deployed')
            )
        )
    ).scalar()

    # Use Temporal task executor
    task_executor = get_task_executor()
    
    task_submission = TaskSubmission(
        task_name="generate_student_template_v2",
        parameters={
            "course_id": course_id,
            "student_template_url": student_template_url,
            "assignments_url": assignments_url,
            "commit_message": request.commit_message or f"Update student template - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            "force_redeploy": request.force_redeploy,
            # Pass through optional release selection for strict commit/path control
            "release": (request.release.model_dump() if request.release else None),
        },
        queue="computor-tasks"
    )
    
    workflow_id = await task_executor.submit_task(task_submission)
    
    # Don't update status here - let the workflow handle all status transitions
    # Just count how many deployments are ready to process
    statuses_to_count = ["pending", "failed"]
    if request.force_redeploy:
        statuses_to_count.append("deployed")
    
    deployment_ids = db.query(CourseContentDeployment.id).join(
        CourseContent,
        CourseContentDeployment.course_content_id == CourseContent.id
    ).filter(
        and_(
            CourseContent.course_id == course_id,
            CourseContentDeployment.deployment_status.in_(statuses_to_count)
        )
    ).all()
    
    return GenerateTemplateResponse(
        workflow_id=workflow_id,
        status="started",
        contents_to_process=len(deployment_ids) if deployment_ids else 0
    )

@system_router.post(
    "/courses/{course_id}/generate-assignments",
    response_model=GenerateAssignmentsResponse
)
async def generate_assignments(
    course_id: str,
    request: GenerateAssignmentsRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    # Permissions
    if check_course_permissions(permissions, Course, "_lecturer", db).filter(Course.id == course_id).first() is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Course {course_id} not found")

    # Determine assignments URL if not provided
    assignments_url = request.assignments_url
    if not assignments_url and course.properties and 'gitlab' in course.properties:
        course_gitlab = course.properties['gitlab']
        if 'assignments_url' in course_gitlab:
            assignments_url = course_gitlab['assignments_url']
        elif 'full_path' in course_gitlab:
            family = db.query(CourseFamily).filter(CourseFamily.id == course.course_family_id).first()
            if not family:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course family not found")
            org = db.query(Organization).filter(Organization.id == family.organization_id).first()
            gitlab_url = (org.properties or {}).get('gitlab', {}).get('url') if org and org.properties else None
            if gitlab_url:
                assignments_url = f"{gitlab_url}/{course_gitlab['full_path']}/assignments"

    # PRE-FLIGHT VALIDATION: Check that selected assignments have valid examples
    is_valid, validation_errors = validate_course_contents_for_release(
        course_id=course_id,
        course_content_ids=request.course_content_ids if request.course_content_ids else None,
        db=db,
        force_redeploy=False,  # Assignments repository doesn't support force_redeploy
        parent_id=request.parent_id,
        include_descendants=request.include_descendants,
        all_flag=request.all
    )

    if not is_valid:
        logger.error(
            f"Release validation failed for assignments in course {course_id}: "
            f"{len(validation_errors)} issues found"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ReleaseValidationError(
                error="Cannot release assignments: Some assignments are missing examples or have invalid deployments",
                validation_errors=validation_errors,
                total_issues=len(validation_errors)
            ).model_dump()
        )

    logger.info(f"Pre-flight validation passed for assignments in course {course_id}")

    # Count selected contents (best-effort)
    contents_q = db.query(func.count(CourseContent.id)).filter(CourseContent.course_id == course_id)
    if request.course_content_ids:
        contents_q = contents_q.filter(CourseContent.id.in_(request.course_content_ids))
    count_estimate = contents_q.scalar()

    # Submit Temporal workflow
    task_executor = get_task_executor()
    selection = {
        'course_content_ids': request.course_content_ids,
        'parent_id': request.parent_id,
        'include_descendants': request.include_descendants,
        'all': request.all,
    }
    task_submission = TaskSubmission(
        task_name="generate_assignments_repository",
        parameters={
            'course_id': course_id,
            'assignments_url': assignments_url,
            'selection': selection,
            'overwrite_strategy': request.overwrite_strategy,
            'commit_message': request.commit_message,
        },
        queue="computor-tasks"
    )
    workflow_id = await task_executor.submit_task(task_submission)

    return GenerateAssignmentsResponse(
        workflow_id=workflow_id,
        status="started",
        contents_to_process=count_estimate or 0
    )

# @system_router.post(
#     "/courses/{course_id}/assign-examples",
#     response_model=Dict[str, Any]
# )
# async def bulk_assign_examples(
#     course_id: str,
#     request: BulkAssignExamplesRequest,
#     permissions: Annotated[Principal, Depends(get_current_principal)],
#     db: Session = Depends(get_db),
#     cache: Annotated[BaseCache, Depends(get_redis_client)] = None
# ):
#     """
#     Assign multiple examples to course contents in bulk (database only).
#     """
#     # Check permissions
#     if check_course_permissions(permissions, Course, "_lecturer", db).filter(Course.id == course_id).first() is None:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to modify this course"
#         )
    
#     # Verify course exists
#     course = db.query(Course).filter(Course.id == course_id).first()
#     if not course:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Course {course_id} not found"
#         )
    
#     assigned = 0
#     updated = 0
#     failed = 0
    
#     for assignment in request.assignments:
#         try:
#             content_id = assignment.get("course_content_id")
#             example_id = assignment.get("example_id")
#             example_version = assignment.get("example_version", "latest")
            
#             # Get course content
#             content = db.query(CourseContent).filter(
#                 and_(
#                     CourseContent.id == content_id,
#                     CourseContent.course_id == course_id
#                 )
#             ).first()
            
#             if not content:
#                 failed += 1
#                 continue
            
#             # Check if already has an example
#             is_update = content.example_id is not None
            
#             # Assign example
#             content.example_id = example_id if example_id else None
#             content.example_version = example_version
#             content.deployment_status = "pending_release"
            
#             if is_update:
#                 updated += 1
#             else:
#                 assigned += 1
                
#         except Exception:
#             failed += 1
#             continue
    
#     db.commit()
    
#     # Clear cache
#     if cache:
#         await cache.delete(f"course:{course_id}:contents")
    
#     return {
#         "assigned": assigned,
#         "updated": updated,
#         "failed": failed
#     }

@system_router.get(
    "/courses/{course_id}/gitlab-status",
    response_model=Dict[str, Any]
)
async def get_course_gitlab_status(
    course_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Check GitLab configuration status for a course.
    
    Returns information about GitLab integration and what's missing.
    """
    # Check permissions
    if check_course_permissions(permissions, Course, "_lecturer", db).filter(Course.id == course_id).first() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this course"
        )
    
    # Get course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course {course_id} not found"
        )
    
    # Check GitLab configuration
    status = {
        "course_id": course_id,
        "has_gitlab_config": False,
        "has_group_id": False,
        "has_student_template_url": False,
        "gitlab_config": {},
        "missing_items": [],
        "recommendations": []
    }
    
    if course.properties and "gitlab" in course.properties:
        status["has_gitlab_config"] = True
        gitlab_props = course.properties["gitlab"]
        
        # Check for group ID
        if "group_id" in gitlab_props:
            status["has_group_id"] = True
            status["gitlab_config"]["group_id"] = gitlab_props["group_id"]
        else:
            status["missing_items"].append("GitLab group ID")
            
        # Check for student template URL
        if "student_template_url" in gitlab_props:
            status["has_student_template_url"] = True
            status["gitlab_config"]["student_template_url"] = gitlab_props["student_template_url"]
        else:
            status["missing_items"].append("Student template repository URL")
            
        # Check for other GitLab properties
        if "projects" in gitlab_props:
            status["gitlab_config"]["projects"] = gitlab_props["projects"]
            
    else:
        status["missing_items"].append("GitLab configuration")
        
    # Get course family for additional context
    if course.course_family_id:
        family = db.query(CourseFamily).filter(CourseFamily.id == course.course_family_id).first()
        if family and family.properties and "gitlab" in family.properties:
            status["course_family_gitlab"] = {
                "has_config": True,
                "group_id": family.properties["gitlab"].get("group_id")
            }
            
    # Add recommendations
    if not status["has_gitlab_config"]:
        status["recommendations"].append(
            "The course needs to be created with GitLab integration enabled. "
            "Please recreate the course or contact an administrator to enable GitLab integration."
        )
    elif not status["has_student_template_url"]:
        status["recommendations"].append(
            "The course has partial GitLab configuration but is missing the student-template repository. "
            "The course may need to be recreated or the GitLab projects need to be created manually."
        )
        
    status["can_generate_template"] = status["has_student_template_url"]
    
    return status

# DEPLOYMENT CONFIGURATION ENDPOINTS

@system_router.post("/hierarchy/create", response_model=dict)
async def create_hierarchy(
    payload: dict,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Create a complete organization -> course family -> course hierarchy from a configuration.
    
    This endpoint accepts a deployment configuration and creates the entire hierarchy
    using the DeployComputorHierarchyWorkflow Temporal workflow.
    """
    # Check admin permissions
    if not check_admin(permissions):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can deploy configurations"
        )
    
    # Extract configuration
    deployment_config = payload.get("deployment_config")
    validate_only = payload.get("validate_only", False)
    
    if not deployment_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="deployment_config is required"
        )
    
    # Validate the configuration structure
    from computor_types.deployments_refactored import ComputorDeploymentConfig
    try:
        config = ComputorDeploymentConfig(**deployment_config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid deployment configuration: {str(e)}"
        )
    
    if validate_only:
        return {
            "status": "validated",
            "message": "Configuration is valid",
            "deployment_path": config.get_full_course_path()
        }
    
    # Submit to Temporal workflow
    task_executor = get_task_executor()
    
    task_submission = TaskSubmission(
        task_name="deploy_computor_hierarchy",
        parameters={
            "deployment_config": config.model_dump(),
            "user_id": permissions.user_id
        },
        queue="computor-tasks"
    )
    
    workflow_id = await task_executor.submit_task(task_submission)
    
    # Get first organization name for message
    org_name = config.organizations[0].name if config.organizations else "Unknown Organization"
    
    return {
        "workflow_id": workflow_id,
        "status": "started",
        "deployment_path": config.get_full_course_path(),
        "message": f"Deployment started for {org_name}"
    }

@system_router.get("/hierarchy/status/{workflow_id}", response_model=dict)
async def get_hierarchy_status(
    workflow_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)]
):
    """
    Get the status of a deployment workflow.
    
    Returns the current status of the deployment workflow, including any errors
    or the final result if completed.
    """
    task_executor = get_task_executor()
    
    try:
        # Get workflow status
        result = await task_executor.get_task_status(workflow_id)
        
        if result:
            # Map status to what CLI expects
            status = result.status_display.lower()
            if status == "finished":
                status = "completed"  # CLI expects "completed" not "finished"
            
            return {
                "workflow_id": workflow_id,
                "status": status,
                "error": result.error,
                "result": None,  # TaskInfo doesn't have result field
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "completed_at": result.completed_at.isoformat() if result.completed_at else None
            }
        else:
            return {
                "workflow_id": workflow_id,
                "status": "not_found",
                "error": "Workflow not found or expired"
            }
    except Exception as e:
        logger.error(f"Error getting deployment status: {e}")
        return {
            "workflow_id": workflow_id,
            "status": "error",
            "error": str(e)
        }
