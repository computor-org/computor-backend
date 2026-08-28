"""Endpoint for deploying a single course from an uploaded course_deployment.yaml.

Backs the optional "upload a course file" path on the web create-course page:
``POST /course-families/{course_family_id}/deploy-course`` with the raw YAML and
a ``validate_only`` flag. The YAML is a top-level ``HierarchicalCourseConfig``
(no organizations/git/users). See ``business_logic/course_deployment.py``.
"""
import logging
from typing import Annotated
from uuid import UUID

import yaml
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from computor_backend.database import get_db
from computor_backend.exceptions import BadRequestException
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.business_logic.course_deployment import deploy_course_from_config
from computor_backend.business_logic.course_ownership import invalidate_creator_caches

from computor_types.course_deployment import CourseDeployRequest, CourseDeployResult
from computor_types.deployment_config import HierarchicalCourseConfig

logger = logging.getLogger(__name__)

course_deployment_router = APIRouter()


@course_deployment_router.post(
    "/course-families/{course_family_id}/deploy-course",
    response_model=CourseDeployResult,
)
async def deploy_course(
    course_family_id: UUID | str,
    request: CourseDeployRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    http_request: Request,
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

    result = await run_in_threadpool(
        deploy_course_from_config,
        db,
        permissions,
        course_family_id,
        config,
        request.validate_only,
    )

    # An applied deploy enrolled the caller as the course's ``_owner``
    # (business_logic.course_ownership), so their authorization changed inside
    # this request. Drop what would otherwise report them role-less on the
    # course they just created — the web navigates straight to it.
    if result.applied and result.course_id:
        await _refresh_caller_permissions(permissions.user_id, http_request)

    return result


async def _refresh_caller_permissions(user_id: str, http_request: Request) -> None:
    """Best-effort cache busting; a stale cache must never fail a good write.

    The Principal cache is keyed by the raw credential, so it is re-parsed off
    the request here rather than declared as a second auth dependency (see
    ``CrudRouter._invalidate_creator_principal`` for why).
    """
    try:
        from computor_backend.business_logic.auth import (
            invalidate_principal_cache_for_token,
        )
        from computor_backend.permissions.auth import parse_authorization_header
        from computor_backend.redis_cache import get_redis_client

        invalidate_creator_caches(str(user_id))
        token = getattr(parse_authorization_header(http_request), "token", None)
        if token:
            await invalidate_principal_cache_for_token(
                token, await get_redis_client()
            )
    except Exception:
        logger.warning(
            "Cache invalidation after course deploy failed", exc_info=True
        )
