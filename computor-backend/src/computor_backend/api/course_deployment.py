"""Endpoint for deploying a single course from an uploaded course_deployment.yaml.

Backs the optional "upload a course file" path on the web create-course page:
``POST /course-families/{course_family_id}/deploy-course`` with the raw YAML and
a ``validate_only`` flag. The YAML is a top-level ``HierarchicalCourseConfig``
(no organizations/git/users). See ``business_logic/course_deployment.py``.
"""
from typing import Annotated
from uuid import UUID

import yaml
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from computor_backend.database import get_db
from computor_backend.exceptions import BadRequestException
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.business_logic.course_deployment import deploy_course_from_config

from computor_types.course_deployment import CourseDeployRequest, CourseDeployResult
from computor_types.deployments_refactored import HierarchicalCourseConfig

course_deployment_router = APIRouter()


@course_deployment_router.post(
    "/course-families/{course_family_id}/deploy-course",
    response_model=CourseDeployResult,
)
async def deploy_course(
    course_family_id: UUID | str,
    request: CourseDeployRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Validate (and optionally apply) a single-course deployment under a family.

    Raises:
        400: invalid YAML / config, or (on apply) blocking validation errors
        403: caller may not create courses in this family
        404: course family not found
    """
    try:
        data = yaml.safe_load(request.yaml)
    except yaml.YAMLError as e:
        raise BadRequestException(detail=f"Invalid YAML: {e}") from e

    if not isinstance(data, dict):
        raise BadRequestException(
            detail="The file must describe a single course (a mapping at the top level)"
        )

    try:
        config = HierarchicalCourseConfig(**data)
    except Exception as e:  # pydantic ValidationError -> 400
        raise BadRequestException(detail=f"Invalid course configuration: {e}") from e

    return await run_in_threadpool(
        deploy_course_from_config,
        db,
        permissions,
        course_family_id,
        config,
        request.validate_only,
    )
