"""Pydantic DTOs for lecturer course content operations."""
from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict, Field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .deployment import CourseContentDeploymentGet, CourseContentDeploymentList

from computor_types.course_content_types import CourseContentTypeGet, CourseContentTypeList
from computor_types.deployments import GitLabConfigGet
from computor_types.base import EntityInterface, ListQuery

from computor_types.custom_types import Ltree

class CourseContentRepositoryLecturerGet(BaseModel):
    """Repository information for course content in lecturer view."""
    url: Optional[str] = None
    full_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CourseContentLecturerGet(BaseModel):
    """DTO for lecturer GET of course content with course repository info."""
    id: str
    archived_at: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: str
    course_id: str
    course_content_type_id: str
    course_content_kind_id: str
    position: float
    max_group_size: Optional[int] = None
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    execution_backend_id: Optional[str] = None
    is_submittable: bool = False
    has_deployment: Optional[bool] = None
    deployment_status: Optional[str] = None

    course_content_type: Optional[CourseContentTypeGet] = None
    repository: CourseContentRepositoryLecturerGet  # GitLab info from course.properties.gitlab

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

class CourseContentLecturerList(BaseModel):
    """DTO for lecturer list of course content with course repository info."""
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
    is_submittable: bool = False
    has_deployment: Optional[bool] = None
    deployment_status: Optional[str] = None

    course_content_type: Optional[CourseContentTypeList] = None
    repository: CourseContentRepositoryLecturerGet  # GitLab info from course.properties.gitlab

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

class CourseContentLecturerQuery(ListQuery):
    """Query parameters for lecturer course content."""
    id: Optional[str] = None
    title: Optional[str] = None
    path: Optional[str] = None
    course_id: Optional[str] = None
    course_content_type_id: Optional[str] = None
    archived: Optional[bool] = None
    position: Optional[float] = None
    max_group_size: Optional[int] = None
    max_test_runs: Optional[int] = None
    max_submissions: Optional[int] = None
    execution_backend_id: Optional[str] = None
    has_deployment: Optional[bool] = Field(
        None,
        description="Filter by whether content has a deployment"
    )

    # GitLab-specific filters (query JSONB properties.gitlab)
    directory: Optional[str] = None
    project: Optional[str] = None
    provider_url: Optional[str] = None

    # Ltree hierarchy filters
    nlevel: Optional[int] = None
    descendants: Optional[str] = None
    ascendants: Optional[str] = None

# BACKEND FUNCTION - Moved to backend in Phase 4
# def course_content_lecturer_search(db: 'Session', query, params: Optional[CourseContentLecturerQuery]):
#     """Search course content based on query parameters for lecturer view.
#
#     This function uses SQLAlchemy models (CourseContent, CourseContentDeployment, etc.)
#     and column references (id, title, path, etc.) that only exist in the backend.
#     It has been moved to the backend business logic layer.
#     """
#     from sqlalchemy.orm import joinedload
#
#     # Always eager load deployment, course_content_type, and course for lecturer views
#     query = query.options(
#         joinedload(CourseContent.deployment),
#         joinedload(CourseContent.course_content_type),
#         joinedload(CourseContent.course)
#     )
#
#     if params.id is not None:
#         query = query.filter(id == params.id)
#     if params.title is not None:
#         query = query.filter(title == params.title)
#     if params.path is not None:
#         if params.path.endswith(".") or params.path.startswith("."):
#             params.path = params.path.strip(".")
#         query = query.filter(path == Ltree(params.path))
#     if params.course_id is not None:
#         query = query.filter(course_id == params.course_id)
#     if params.course_content_type_id is not None:
#         query = query.filter(course_content_type_id == params.course_content_type_id)
#     if params.position is not None:
#         query = query.filter(position == params.position)
#     if params.max_group_size is not None:
#         query = query.filter(max_group_size == params.max_group_size)
#     if params.max_test_runs is not None:
#         query = query.filter(max_test_runs == params.max_test_runs)
#     if params.max_submissions is not None:
#         query = query.filter(max_submissions == params.max_submissions)
#     if params.execution_backend_id is not None:
#         query = query.filter(execution_backend_id == params.execution_backend_id)
#
#     if params.archived is not None and params.archived is not False:
#         query = query.filter(archived_at != None)
#     else:
#         query = query.filter(archived_at == None)
#
#     # Filter by deployment status if requested
#     if params.has_deployment is not None:
#         if params.has_deployment:
#             query = query.filter(
#                 db.query(CourseContentDeployment)
#                 .filter(course_content_id == CourseContent.id)
#                 .exists()
#             )
#         else:
#             query = query.filter(
#                 ~db.query(CourseContentDeployment)
#                 .filter(course_content_id == CourseContent.id)
#                 .exists()
#             )
#
#     return query

class CourseContentLecturerInterface(EntityInterface):
    """Interface for lecturer course content operations."""
    get = CourseContentLecturerGet
    list = CourseContentLecturerList
    query = CourseContentLecturerQuery

    # Note: This is a VIEW endpoint (read-only), not standard CRUD
    # Mounted at /lecturers/course-contents in backend
    # Only supports GET list and GET by id operations

# Fix forward references
from .deployment import CourseContentDeploymentGet, CourseContentDeploymentList

CourseContentLecturerGet.model_rebuild()
CourseContentLecturerList.model_rebuild()