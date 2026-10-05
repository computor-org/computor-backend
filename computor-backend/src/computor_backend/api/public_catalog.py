"""Anonymous, read-only public course discovery and learning reader.

GET /courses/public stays authenticated because it is caller-relative.  The
routes here are the deliberately narrow anonymous projection: public courses,
their learner-visible pedagogical outline, and assignment descriptions/media.
No repository credentials, tests, solutions, submissions, or instructor files
cross this boundary.
"""

import math
import mimetypes
import threading
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from computor_backend.business_logic.course_registration import list_anonymous_catalog
from computor_backend.business_logic.public_learning import (
    available_description_languages,
    description_files,
    load_public_course_outline,
    resolve_public_asset_source,
    resolve_public_content_source,
    select_description_file,
)
from computor_backend.database import get_db_session
from computor_backend.exceptions import NotFoundException
from computor_backend.services.storage_service import get_storage_service
from computor_types.courses import CoursePublicCatalogEntry
from computor_types.public_learning import (
    PublicLearningContentGet,
    PublicLearningCourseOutline,
    PublicLearningResources,
)

PUBLIC_CATALOG_TTL = 60.0

public_catalog_router = APIRouter(prefix="/public", tags=["public"])

_lock = threading.Lock()
_cache: tuple[float, list[CoursePublicCatalogEntry]] | None = None
# Indirections so tests can drive the clock and bind the session.
_clock = time.monotonic
_session_factory = get_db_session


def clear_public_catalog_cache() -> None:
    """Drop the cached catalog (tests; also usable after bulk course changes)."""
    global _cache
    with _lock:
        _cache = None


@public_catalog_router.get(
    "/courses",
    response_model=list[CoursePublicCatalogEntry],
    summary="Public course catalog for visitors who are not signed in",
)
def list_public_catalog(response: Response) -> list[CoursePublicCatalogEntry]:
    """Courses open for self-registration. No authentication, no member data."""
    global _cache
    # Held across the refresh on purpose: concurrent misses wait for the one
    # query in flight and then read its result. Waiters hold no connection.
    with _lock:
        now = _clock()
        if _cache is None or now - _cache[0] >= PUBLIC_CATALOG_TTL:
            with _session_factory() as db:
                items = list_anonymous_catalog(db)
            _cache = (now, items)
        fetched_at, items = _cache
    remaining = max(0, math.floor(PUBLIC_CATALOG_TTL - (now - fetched_at)))
    response.headers["Cache-Control"] = f"public, max-age={remaining}"
    return items


@public_catalog_router.get(
    "/courses/{course_id}/outline",
    response_model=PublicLearningCourseOutline,
    summary="Browse the learner-visible outline of one public course",
)
def public_course_outline(
    course_id: UUID | str,
    response: Response,
) -> PublicLearningCourseOutline:
    """Pedagogical hierarchy only; hidden/unreleased content is absent."""
    with _session_factory() as db:
        outline = load_public_course_outline(db, course_id)
    response.headers["Cache-Control"] = "public, max-age=60"
    return outline


@public_catalog_router.get(
    "/course-contents/{content_id}",
    response_model=PublicLearningContentGet,
    summary="Read one learner-visible public course item",
)
async def public_course_content(
    content_id: UUID | str,
    response: Response,
    language: Optional[str] = Query(
        None,
        max_length=16,
        description="Preferred description language, e.g. de or en",
    ),
    storage_service=Depends(get_storage_service),
) -> PublicLearningContentGet:
    """Return Markdown from the deployed example's public description directory.

    Only top-level index/README description files are candidates. The storage
    location is resolved server-side and never returned to the caller.
    """
    with _session_factory() as db:
        source = resolve_public_content_source(db, content_id)

    markdown = source.description or ""
    selected_language = source.course_language
    available_languages: list[str] = []

    if source.bucket_name and source.storage_path:
        objects = await storage_service.list_objects(
            bucket_name=source.bucket_name,
            prefix=f"{source.storage_path.rstrip('/')}/content/",
        )
        files = description_files(
            (obj.object_name for obj in objects),
            source.storage_path,
        )
        selected_language, object_key = select_description_file(
            files,
            requested_language=language,
            course_language=source.course_language,
        )
        available_languages = available_description_languages(files)
        if object_key is not None:
            raw = await storage_service.download_file(
                bucket_name=source.bucket_name,
                object_key=object_key,
            )
            markdown = raw.decode("utf-8", errors="replace")

    response.headers["Cache-Control"] = "public, max-age=60"
    return PublicLearningContentGet(
        id=source.id,
        course_id=source.course_id,
        title=source.title,
        description=source.description,
        path=source.path,
        kind=source.kind,
        is_submittable=source.is_submittable,
        markdown=markdown,
        selected_language=selected_language,
        available_languages=available_languages,
    )


@public_catalog_router.get(
    "/course-contents/{content_id}/assets/{asset_path:path}",
    summary="Read one public assignment-description media asset",
)
async def public_course_content_asset(
    content_id: UUID | str,
    asset_path: str,
    response: Response,
    storage_service=Depends(get_storage_service),
):
    """Serve only content/mediaFiles assets from visible, released public items."""
    with _session_factory() as db:
        source = resolve_public_asset_source(db, content_id, asset_path)

    # Check existence explicitly so a missing asset is an opaque 404 rather than
    # whatever storage-provider error happens to escape from download_file.
    objects = await storage_service.list_objects(
        bucket_name=source.bucket_name,
        prefix=source.object_key,
    )
    if not any(obj.object_name == source.object_key for obj in objects):
        raise NotFoundException(detail="Public asset not found")

    data = await storage_service.download_file(
        bucket_name=source.bucket_name,
        object_key=source.object_key,
    )
    media_type = mimetypes.guess_type(source.object_key)[0] or "application/octet-stream"
    response.headers["Cache-Control"] = "public, max-age=300"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=300"},
    )


@public_catalog_router.get(
    "/learning",
    response_model=PublicLearningResources,
    summary="Independent practice options and public-learning provenance",
)
def public_learning_resources(response: Response) -> PublicLearningResources:
    """Course navigation is native; GitHub remains optional source/provenance."""
    repo = "https://github.com/computor-org/data-science-python"
    response.headers["Cache-Control"] = "public, max-age=300"
    return PublicLearningResources(
        desktop_extension_url=(
            "https://marketplace.visualstudio.com/"
            "items?itemName=computor-org.computor"
        ),
        codespaces_url=(
            "https://codespaces.new/computor-org/"
            "data-science-python?quickstart=1"
        ),
        guide_url="/learn",
        source_url=repo,
    )
