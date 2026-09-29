"""Anonymous, read-only course catalog for the landing page (issue #415).

``GET /courses/public`` stays authenticated by design (it is caller-relative:
it marks the caller's own memberships). Visitors who are not signed in get
this separate endpoint instead: public, visible, non-archived courses with
title, description and language only.

The answer is identical for every caller, so it is cached in-process for
``PUBLIC_CATALOG_TTL`` seconds and marked cacheable for browsers and proxies.
A course that is published or hidden shows up here after at most that long.
"""

import threading
import time

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from computor_backend.business_logic.course_registration import list_anonymous_catalog
from computor_backend.database import get_db
from computor_types.courses import CoursePublicCatalogEntry

PUBLIC_CATALOG_TTL = 60.0

public_catalog_router = APIRouter(prefix="/public", tags=["public"])

_lock = threading.Lock()
_cache: tuple[float, list[CoursePublicCatalogEntry]] | None = None


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
def list_public_catalog(
    response: Response,
    db: Session = Depends(get_db),
) -> list[CoursePublicCatalogEntry]:
    """Courses open for self-registration. No authentication, no member data."""
    global _cache
    now = time.monotonic()
    with _lock:
        cached = _cache
    if cached is None or now - cached[0] >= PUBLIC_CATALOG_TTL:
        # The session connects lazily, so a cache hit costs no DB round trip.
        cached = (now, list_anonymous_catalog(db))
        with _lock:
            _cache = cached
    response.headers["Cache-Control"] = f"public, max-age={int(PUBLIC_CATALOG_TTL)}"
    return cached[1]
