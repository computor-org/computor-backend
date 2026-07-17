import logging
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, Query, Response
from sqlalchemy.orm import Session
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.permissions.principal import Principal

from computor_backend.database import get_db
from computor_backend.api.api_builder import CrudRouter
from computor_backend.exceptions import (
    ForbiddenException,
    NotFoundException,
    RateLimitException,
    ServiceUnavailableException,
)
from computor_backend.interfaces import CourseInterface
from computor_backend.model import Course
from computor_backend.redis_cache import get_redis_client
from computor_backend.services.storage_service import get_storage_service
from computor_backend.business_logic.cascade_deletion import delete_course_cascade
from computor_backend.business_logic.course_git import resolve_template_archive_source
from computor_backend.business_logic.course_template_export import (
    build_hierarchical_mapping,
    remap_archive_to_hierarchy,
)
from computor_types.cascade_deletion import CascadeDeleteResult

logger = logging.getLogger(__name__)

course_router = CrudRouter(CourseInterface)

# Each download pulls the whole template archive from the git server and, in
# hierarchical mode, rebuilds the zip in memory — cheap enough to click a few
# times in a row, not something to hammer.
TEMPLATE_DOWNLOAD_LIMIT = 10
TEMPLATE_DOWNLOAD_WINDOW = 60


async def check_template_download_rate_limit(user_id: str, cache) -> bool:
    """True once the user has spent their template-download budget.

    Fixed window per user, Redis-backed so it holds across workers. Fails open:
    this protects the git server from accidental hammering, it is not a
    security control.
    """
    key = f"rate_limit:template_download:{user_id}"
    try:
        count = await cache.incr(key)
        if count == 1:
            await cache.expire(key, TEMPLATE_DOWNLOAD_WINDOW)
        return count > TEMPLATE_DOWNLOAD_LIMIT
    except Exception as e:
        logger.error(f"Template download rate limit check failed: {e}")
        return False


@course_router.router.get(
    "/{course_id}/template",
    responses={200: {"content": {"application/zip": {}}}},
    summary="Download the course template as a ZIP",
)
async def download_course_template(
    course_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache=Depends(get_redis_client),
    hierarchical: bool = Query(
        default=False,
        description=(
            "false: the student-template repo as it is in git (example "
            "directories). true: directories follow the course-content tree — "
            "unit/assignment titles name the directories; files not belonging "
            "to a deployed assignment are omitted."
        ),
    ),
):
    """Download the current course template, flat or re-arranged hierarchically.

    Rate limit: 10 downloads per minute per user (429 once exhausted).
    """
    if permissions.is_admin or "_organization_manager" in permissions.roles:
        # Global managers reach every course without a membership row.
        course = db.query(Course).filter(Course.id == str(course_id)).first()
    else:
        course = (
            check_course_permissions(permissions, Course, "_lecturer", db)
            .filter(Course.id == str(course_id))
            .first()
        )
    if course is None:
        raise ForbiddenException(
            detail="Downloading the course template requires the lecturer role"
        )

    user_id = permissions.get_user_id()
    if await check_template_download_rate_limit(str(user_id), cache):
        raise RateLimitException(
            error_code="RATE_001",
            detail="Too many template downloads. Please wait before trying again.",
            retry_after=TEMPLATE_DOWNLOAD_WINDOW,
            context={
                "limit": TEMPLATE_DOWNLOAD_LIMIT,
                "window_seconds": TEMPLATE_DOWNLOAD_WINDOW,
            },
        )

    url, headers, filename = resolve_template_archive_source(str(course_id), db)
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        upstream = await client.get(url, headers=headers)
    if upstream.status_code != 200:
        raise ServiceUnavailableException(
            detail="Could not fetch the template archive from the git server.",
            context={"upstream_status": upstream.status_code},
        )

    content = upstream.content
    if hierarchical:
        mapping = build_hierarchical_mapping(str(course_id), db)
        content = remap_archive_to_hierarchy(content, mapping)
        stem = filename[:-4] if filename.endswith(".zip") else filename
        filename = f"{stem}-hierarchical.zip"

    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@course_router.router.delete(
    "/{course_id}",
    response_model=CascadeDeleteResult,
    summary="Delete course and all course-specific data",
    description="""
    Delete a course and ALL its data including:
    - All course members (NOT the users themselves)
    - All course groups
    - All course content types and contents
    - All submission groups and their artifacts
    - All results and grades
    - All messages targeted to the course

    **WARNING**: This is a destructive operation. Use dry_run=true to preview.
    """
)
async def delete_course_endpoint(
    course_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    dry_run: bool = Query(
        default=False,
        description="If true, only returns preview without deleting"
    ),
) -> CascadeDeleteResult:
    """Delete course and all course-specific data."""
    if not permissions.is_admin:
        raise ForbiddenException(detail="Deletion requires admin permissions")

    # Verify course exists
    course = db.query(Course).filter(Course.id == str(course_id)).first()
    if not course:
        raise NotFoundException(detail=f"Course not found: {course_id}")

    storage = get_storage_service()
    result = await delete_course_cascade(
        db=db,
        course_id=str(course_id),
        storage=storage,
        dry_run=dry_run
    )

    return result
