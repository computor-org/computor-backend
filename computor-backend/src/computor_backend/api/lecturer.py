from uuid import UUID
from typing import Annotated
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status

from computor_backend.database import get_db
from computor_backend.redis_cache import get_cache
from computor_backend.cache import Cache
from computor_types.courses import CourseGet, CourseList, CourseQuery
from computor_types.lecturer_course_contents import (
    CourseContentLecturerGet,
    CourseContentLecturerList,
    CourseContentLecturerQuery,
)
from computor_types.lecturer_deployments import (
    AssignExampleRequest,
    AssignExampleResponse,
    DeploymentGet,
    UnassignExampleResponse,
)
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal

# Import business logic
from computor_backend.business_logic.lecturer import (
    get_lecturer_course,
    list_lecturer_courses,
    get_lecturer_course_content,
    list_lecturer_course_contents,
)
from computor_backend.business_logic.lecturer_deployment import (
    assign_example_to_content,
    get_deployment_for_content,
    unassign_example_from_content,
)

lecturer_router = APIRouter()

@lecturer_router.get("/courses/{course_id}", response_model=CourseGet)
def lecturer_get_courses_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Get a specific course for lecturers."""
    return get_lecturer_course(course_id, permissions, db, cache)

@lecturer_router.get("/courses", response_model=list[CourseList])
def lecturer_list_courses_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """List courses accessible to lecturers."""
    return list_lecturer_courses(permissions, params, db, cache)

@lecturer_router.get("/course-contents/{course_content_id}", response_model=CourseContentLecturerGet)
def lecturer_get_course_contents_endpoint(
    course_content_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """Get a specific course content with course repository information."""
    return get_lecturer_course_content(course_content_id, permissions, db, cache)

@lecturer_router.get("/course-contents", response_model=list[CourseContentLecturerList])
def lecturer_list_course_contents_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    params: CourseContentLecturerQuery = Depends(),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache)
):
    """List course contents with course repository information."""
    return list_lecturer_course_contents(permissions, params, db, cache)


# ============================================================================
# Deployment Management Endpoints (Example Assignment)
# ============================================================================

@lecturer_router.post(
    "/course-contents/{course_content_id}/assign-example",
    response_model=AssignExampleResponse
)
def assign_example_to_course_content(
    course_content_id: UUID | str,
    request: AssignExampleRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Assign an example to a course content (assignment).

    This is phase 1 of the release process: Database-only assignment.
    No Git operations are performed at this stage.

    Requirements:
    - User must have _lecturer or higher role in the course
    - Course content must be submittable (assignment type)
    - Example and version must exist in the database
    - Version must follow semantic versioning format

    Args:
        course_content_id: ID of the course content to assign to
        request: Assignment request with example_id and version_tag
        permissions: Current user permissions
        db: Database session

    Returns:
        AssignExampleResponse with deployment details

    Raises:
        400: Invalid request (bad version format, non-submittable content, etc.)
        403: Insufficient permissions
        404: Course content, example, or version not found
    """
    deployment = assign_example_to_content(
        course_content_id=course_content_id,
        example_id=request.example_id,
        version_tag=request.version_tag,
        permissions=permissions,
        db=db
    )

    return AssignExampleResponse(
        deployment_id=str(deployment.id),
        course_content_id=str(deployment.course_content_id),
        example_id=request.example_id,
        example_version_id=str(deployment.example_version_id),
        version_tag=deployment.version_tag,
        deployment_status=deployment.deployment_status,
        assigned_at=deployment.assigned_at,
        message=f"Example '{request.example_id}' (v{request.version_tag}) successfully assigned to course content"
    )


@lecturer_router.get(
    "/course-contents/{course_content_id}/deployment",
    response_model=DeploymentGet
)
def get_course_content_deployment(
    course_content_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Get the current deployment information for a course content.

    Shows which example (if any) is assigned to this course content
    and its deployment status.

    Args:
        course_content_id: ID of the course content
        permissions: Current user permissions
        db: Database session

    Returns:
        DeploymentGet with deployment details

    Raises:
        403: Insufficient permissions
        404: Course content not found or no deployment exists
    """
    deployment = get_deployment_for_content(
        course_content_id=course_content_id,
        permissions=permissions,
        db=db
    )

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No deployment found for course content {course_content_id}"
        )

    # Build enriched response
    example = None
    if deployment.example_version and deployment.example_version.example:
        example = deployment.example_version.example

    course_content = deployment.course_content

    return DeploymentGet(
        id=str(deployment.id),
        course_content_id=str(deployment.course_content_id),
        example_id=str(example.id) if example else None,
        example_version_id=str(deployment.example_version_id) if deployment.example_version_id else None,
        example_identifier=str(deployment.example_identifier) if deployment.example_identifier else None,
        version_tag=deployment.version_tag,
        deployment_status=deployment.deployment_status,
        deployment_message=deployment.deployment_message,
        assigned_at=deployment.assigned_at,
        deployed_at=deployment.deployed_at,
        deployment_path=deployment.deployment_path,
        example_title=example.title if example else None,
        example_directory=example.directory if example else None,
        example_description=example.description if example else None,
        course_content_title=course_content.title if course_content else None,
        course_content_path=str(course_content.path) if course_content else None,
    )


@lecturer_router.delete(
    "/course-contents/{course_content_id}/deployment",
    response_model=UnassignExampleResponse
)
def unassign_example_from_course_content(
    course_content_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Unassign an example from a course content (assignment).

    Only allowed if the example has not been deployed yet.
    Cannot unassign examples that are already deployed or currently deploying.

    Args:
        course_content_id: ID of the course content
        permissions: Current user permissions
        db: Database session

    Returns:
        UnassignExampleResponse with unassignment confirmation

    Raises:
        400: Cannot unassign (already deployed or deploying)
        403: Insufficient permissions
        404: Course content or deployment not found
    """
    result = unassign_example_from_content(
        course_content_id=course_content_id,
        permissions=permissions,
        db=db
    )

    return UnassignExampleResponse(**result)
