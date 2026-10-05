"""Anonymous, read-only course catalog for the landing page (issue #415).

``GET /courses/public`` stays authenticated by design (it is caller-relative:
it marks the caller's own memberships). Visitors who are not signed in get
this separate endpoint instead: public, visible, non-archived courses with
title, description and language only.

The answer is identical for every caller, so it is cached in-process for
``PUBLIC_CATALOG_TTL`` seconds. A course that is published or hidden shows up
here after at most that long, end to end: browsers and proxies are told only
the snapshot's *remaining* freshness (``max-age`` counts down to 0), so a
response served from an old snapshot cannot be kept past the snapshot's own
expiry. Refreshes are coalesced under the lock, so a burst of cold requests
costs one query, not one per request.

The route deliberately has no DB dependency: a request-scoped ``get_db()``
would let every waiter hold a pooled connection (``get_db`` even connects
eagerly when a caller passes ``?user_id=``) while it queues on the lock, and
enough waiters starve the pool the refresh itself needs. Only the request that
actually refreshes opens a short-lived session, and only for the query.
"""

import math
import threading
import time

from fastapi import APIRouter, Response

from computor_backend.business_logic.course_registration import list_anonymous_catalog
from computor_backend.database import get_db_session
from computor_types.courses import CoursePublicCatalogEntry
from computor_types.public_learning import PublicLearningResources

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


@public_catalog_router.get("/learning", response_model=PublicLearningResources,
    summary="Published learning material and independent practice options")
def public_learning_resources(response: Response) -> PublicLearningResources:
    """Curated public links only: no storage access, repository credentials or jobs."""
    repo = "https://github.com/computor-org/data-science-python"
    response.headers["Cache-Control"] = "public, max-age=300"
    return PublicLearningResources(
        courses=[dict(slug=slug, title=title, exercises=count, languages=["de", "en"],
            manifest_url=f"{repo}/blob/main/courses/python-{slug}.yaml",
            examples_url=f"{repo}/tree/main/examples/python", license="MIT OR CC-BY-4.0")
            for slug, title, count in [("beginner", "Data Science mit Python – Grundlagen", 21),
                ("intermediate", "Data Science mit Python – Aufbau", 31),
                ("advanced", "Data Science mit Python – Vertiefung", 18)]],
        desktop_extension_url="https://marketplace.visualstudio.com/items?itemName=computor-org.computor",
        codespaces_url="https://codespaces.new/computor-org/data-science-python?quickstart=1",
        guide_url=f"{repo}/blob/main/docs/GETTING_STARTED.md",
    )
