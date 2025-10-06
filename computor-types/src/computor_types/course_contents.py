from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict, Field
from typing import TYPE_CHECKING, Optional, Dict, Any

from starlette.concurrency import run_in_threadpool
from computor_types.course_content_types import CourseContentTypeGet, CourseContentTypeList
from computor_types.deployments import GitLabConfig, GitLabConfigGet
from computor_types.base import BaseEntityGet, EntityInterface, ListQuery

from computor_types.custom_types import Ltree

if TYPE_CHECKING:
    from .deployment import CourseContentDeploymentGet

# Course Content Properties - deployment history moved to separate deployment table
class CourseContentProperties(BaseModel):
    """Properties for course content (stored in JSONB)."""
    gitlab: Optional[GitLabConfig] = None
    # Additional custom properties can be stored here
    
    model_config = ConfigDict(
        extra='allow',
    )

class CourseContentPropertiesGet(BaseModel):
    """Properties for course content GET responses."""
    gitlab: Optional[GitLabConfigGet] = None
    # Additional custom properties can be included here

    model_config = ConfigDict(
        extra='allow',
    )
    
class CourseContentCreate(BaseModel):
    """DTO for creating course content."""
    title: Optional[str] = None
    description: Optional[str] = None
    path: str
    course_id: str
    course_content_type_id: str
    properties: Optional[CourseContentProperties] = None
    position: float = 0
    max_group_size: Optional[int] = None
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    execution_backend_id: Optional[str] = None
    # Note: Example assignments are now handled through the deployment API
    # Use POST /course-contents/{id}/assign-example instead

    model_config = ConfigDict(use_enum_values=True)

class CourseContentGet(BaseEntityGet):
    """DTO for course content GET responses."""
    id: str
    archived_at: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: str
    course_id: str
    course_content_type_id: str
    course_content_kind_id: str
    properties: Optional[CourseContentPropertiesGet] = None
    position: float
    max_group_size: Optional[int] = None
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    execution_backend_id: Optional[str] = None
    is_submittable: bool = False  # From model's column_property
    has_deployment: Optional[bool] = None  # From model's @property
    deployment_status: Optional[str] = None  # From model's @property
    
    # Deprecated fields - kept for backwards compatibility during migration
    # These will be removed in a future version
    # Access deployment info via GET /course-contents/{id}/deployment instead
    example_version_id: Optional[str] = Field(
        None, 
        deprecated=True,
        description="DEPRECATED: Use deployment API"
    )

    course_content_type: Optional[CourseContentTypeGet] = None
    
    # Optional deployment summary (populated when requested)
    deployment: Optional['CourseContentDeploymentGet'] = Field(
        None,
        description="Deployment information if requested via include=deployment"
    )

    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    
class CourseContentList(BaseModel):
    """DTO for course content list responses."""
    id: str
    title: Optional[str] = None
    path: str
    course_id: str
    course_content_type_id: str
    course_content_kind_id: str
    position: float
    max_group_size: Optional[int] = None
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    execution_backend_id: Optional[str] = None
    is_submittable: bool = False  # Add this field to list view
    
    course_content_type: Optional['CourseContentTypeList'] = None
    
    # Optional deployment summary for list views
    has_deployment: Optional[bool] = Field(
        None,
        description="Whether this content has an example deployment"
    )
    deployment_status: Optional[str] = Field(
        None,
        description="Current deployment status if has_deployment=true"
    )

    # Optional deployment summary (populated when requested)
    deployment: Optional['CourseContentDeploymentList'] = Field(
        None,
        description="Deployment information if requested via include=deployment"
    )
    
    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)
    

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    
class CourseContentUpdate(BaseModel):
    """DTO for updating course content."""
    path: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    course_content_type_id: Optional[str] = None
    properties: Optional[CourseContentProperties] = None
    position: Optional[float] = None
    max_group_size: Optional[int] = None
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    execution_backend_id: Optional[str] = None
    # Note: Example assignments cannot be updated here
    # Use the deployment API endpoints instead

class CourseContentQuery(ListQuery):
    """Query parameters for course content."""
    id: Optional[str] = None
    title: Optional[str] = None
    path: Optional[str] = None
    course_id: Optional[str] = None
    course_content_type_id: Optional[str] = None
    properties: Optional[CourseContentProperties] = None
    archived: Optional[bool] = None
    position: Optional[float] = None
    max_group_size: Optional[int] = None
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    execution_backend_id: Optional[str] = None
    # Deployment filtering is done via separate deployment endpoints
    has_deployment: Optional[bool] = Field(
        None,
        description="Filter by whether content has a deployment"
    )

# BACKEND FUNCTION - Moved to backend in Phase 4
# def course_content_search(db: 'Session', query, params: Optional[CourseContentQuery]):
#     """Search course content based on query parameters."""
#     from sqlalchemy.orm import joinedload
#
#     # Always eager load deployment and course_content_type for list views
#     query = query.options(
#         joinedload(CourseContent.deployment),
#         joinedload(CourseContent.course_content_type)
#     )
#
#     if params.id != None:
#         query = query.filter(id == params.id)
#     if params.title != None:
#         query = query.filter(title == params.title)
#     if params.path != None:
#
#         if params.path.endswith(".") or params.path.startswith("."):
#             params.path = params.path.strip(".")
#
#         query = query.filter(path == Ltree(params.path))
#
#     if params.course_id != None:
#         query = query.filter(course_id == params.course_id)
#     if params.course_content_type_id != None:
#         query = query.filter(course_content_type_id == params.course_content_type_id)
#     if params.position != None:
#         query = query.filter(position == params.position)
#     if params.max_group_size != None:
#         query = query.filter(max_group_size == params.max_group_size)
#     if params.max_test_runs != None:
#         query = query.filter(max_test_runs == params.max_test_runs)
#     if params.max_submissions != None:
#         query = query.filter(max_submissions == params.max_submissions)
#     if params.execution_backend_id != None:
#         query = query.filter(execution_backend_id == params.execution_backend_id)
#
#     if params.archived != None and params.archived != False:
#         query = query.filter(archived_at != None)
#     else:
#         query = query.filter(archived_at == None)
#
#     # Filter by deployment status if requested
#     if params.has_deployment is not None:
#         if params.has_deployment:
#             # Has deployment - use exists subquery
#             query = query.filter(
#                 db.query(CourseContentDeployment)
#                 .filter(course_content_id == CourseContent.id)
#                 .exists()
#             )
#         else:
#             # No deployment - use not exists subquery
#             query = query.filter(
#                 ~db.query(CourseContentDeployment)
#                 .filter(course_content_id == CourseContent.id)
#                 .exists()
#             )
#
#     return query
#
# BACKEND FUNCTION - Moved to backend in Phase 4
# async def post_create(course_content: CourseContent, db: Session):
#     """Post-create hook for course content.
#
#     Creates submission groups for individual assignments.
#     Note: Deployment records are created separately via the deployment API.
#     """
#     import logging
#     logger = logging.getLogger(__name__)
#
#     logger.info(f"post_create called for CourseContent {course_content.id} in course {course_content.course_id}")
#
#     # Only create submission groups for individual assignments (max_group_size == 1)
#     # Team assignments (max_group_size > 1) are handled differently
#     if course_content.max_group_size != 1 and course_content.max_group_size != None:
#         logger.info(f"Skipping submission group creation: max_group_size={course_content.max_group_size} (not individual)")
#         return
#
#     # Wrap all database operations in threadpool
#     def _create_submission_groups():
#         # Check if this course content type is submittable
#         course_content_type = db.query(CourseContentType).filter(
#             CourseContentType.id == course_content.course_content_type_id
#         ).first()
#
#         if not course_content_type:
#             logger.warning(f"CourseContentType {course_content.course_content_type_id} not found")
#             return
#
#         course_content_kind = db.query(CourseContentKind).filter(
#             CourseContentKind.id == course_content_type.course_content_kind_id
#         ).first()
#
#         if not course_content_kind or not course_content_kind.submittable:
#             logger.info(f"Skipping submission group creation: not submittable (kind={course_content_kind})")
#             return
#
#         # Get all student course members (not tutors, lecturers, etc.)
#         course_members = (
#             db.scalars(db.query(CourseMember.id)
#             .join(User, User.id == CourseMember.user_id)
#             .filter(
#                 CourseMember.course_id == course_content.course_id,
#                 User.user_type == "user"
#             )).all()
#         )
#
#         logger.info(f"Found {len(course_members)} students in course {course_content.course_id}")
#
#         submission_groups_created = 0
#         for course_member_id in course_members:
#             # Get the full course member object to access properties
#             course_member = db.query(CourseMember).filter(id == course_member_id).first()
#             if not course_member:
#                 logger.warning(f"Could not find CourseMember {course_member_id}")
#                 continue
#
#             submission_group = SubmissionGroup(
#                 course_id=course_content.course_id,
#                 course_content_id=course_content.id,
#                 max_group_size=course_content.max_group_size or 1,
#                 max_test_runs=course_content.max_test_runs,
#                 max_submissions=course_content.max_submissions
#             )
#
#             # Copy repository info from course member if it exists
#             if course_member.properties:
#                 logger.info(f"CourseMember {course_member.id} properties: {course_member.properties}")
#                 if 'gitlab' in course_member.properties:
#                     # Initialize properties if needed
#                     if not submission_group.properties:
#                         submission_group.properties = {}
#
#                     repo_info = course_member.properties
#
#                     # Store in the GitLabConfig format expected by SubmissionGroupProperties
#                     submission_group.properties['gitlab'] = {
#                         "url": repo_info['gitlab']['url'],
#                         "full_path": repo_info['gitlab']['full_path'],
#                         "directory": str(course_content.path),  # Assignment path
#                         "web_url": repo_info['gitlab']['web_url'],
#                         "group_id": repo_info['gitlab']['group_id'],
#                         "namespace_id": repo_info['gitlab']['namespace_id'],
#                         "namespace_path": repo_info['gitlab']['namespace_path']
#                     }
#
#                     logger.info(f"Copying gitlab info to submission group for student {course_member.id}")
#                 else:
#                     logger.info(f"No gitlab in properties for student {course_member.id}")
#             else:
#                 logger.info(f"No properties for student {course_member.id}")
#
#             db.add(submission_group)
#             db.commit()
#             db.refresh(submission_group)
#
#             submission_group_member = SubmissionGroupMember(
#                 submission_group_id = submission_group.id,
#                 course_member_id = course_member.id,  # Use the course_member object's id
#                 course_id = course_content.course_id  # Add course_id for consistency
#             )
#
#             db.add(submission_group_member)
#             db.commit()
#             db.refresh(submission_group_member)
#
#             submission_groups_created += 1
#             logger.info(f"Created submission group {submission_group.id} and member for student {course_member.id}")
#
#         logger.info(f"Created {submission_groups_created} submission groups for CourseContent {course_content.id}")
#
#     await run_in_threadpool(_create_submission_groups)
#
# BACKEND FUNCTION - Moved to backend in Phase 4
# async def post_update(updated_item: CourseContent, old_item: CourseContentGet, db: Session):
#     """Handle path updates for course content descendants after parent is updated"""
#     # Check if path has changed
#     if str(old_item.path) != str(updated_item.path):
#         old_path = str(old_item.path)
#         new_path = str(updated_item.path)
#
#         # Wrap all database operations in threadpool
#         def _update_descendant_paths():
#             try:
#                 # Find all descendants using text() to avoid relationship loading issues
#                 from sqlalchemy import text
#                 descendants = db.query(CourseContent).filter(
#                     text("course_content.path::text LIKE :pattern"),
#                     CourseContent.course_id == updated_item.course_id
#                 ).params(pattern=f'{old_path}.%').all()
#
#                 # Update paths of all descendants using direct SQL update
#                 for descendant in descendants:
#                     old_descendant_path = str(descendant.path)
#
#                     # Replace the old parent path with the new parent path
#                     if old_descendant_path.startswith(old_path + '.'):
#                         # Remove the old parent path and add the new parent path
#                         relative_path = old_descendant_path[len(old_path):]  # includes the leading '.'
#                         new_descendant_path = new_path + relative_path
#
#                         # Use direct SQL update to ensure it gets committed
#                         db.execute(
#                             text("UPDATE course_content SET path = :new_path WHERE id = :content_id"),
#                             {"new_path": new_descendant_path, "content_id": descendant.id}
#                         )
#
#                 # Force commit the descendant changes immediately
#                 db.commit()
#
#                 # Refresh the updated_item to ensure it's still attached to the session
#                 db.refresh(updated_item)
#
#             except Exception as e:
#                 print(f"Error in post_update: {e}")
#                 db.rollback()
#                 raise
#
#         await run_in_threadpool(_update_descendant_paths)
#
class CourseContentInterface(EntityInterface):
    """Interface for CourseContent entity.
    
    Note: Example deployments are managed through the deployment API.
    Use CourseContentDeploymentInterface for deployment operations.
    """
    create = CourseContentCreate
    get = CourseContentGet
    list = CourseContentList  # Use CourseContentList for list views
    update = CourseContentUpdate
    query = CourseContentQuery
    # post_create = post_create  # Moved to backend in Phase 4
    # post_update = post_update  # Moved to backend in Phase 4

# Rebuild models to resolve forward references
# Import the necessary types first
from .example import ExampleVersionGet
from .deployment import CourseContentDeploymentGet, CourseContentDeploymentList, DeploymentHistoryGet

# Rebuild all models that have forward references
CourseContentDeploymentGet.model_rebuild()
DeploymentHistoryGet.model_rebuild()
CourseContentGet.model_rebuild()