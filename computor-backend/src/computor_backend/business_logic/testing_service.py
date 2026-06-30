"""Resolve the testing :class:`Service` for a course content.

``CourseContent.testing_service_id`` is a *cache*, not the source of truth — the
source of truth is the deployed example's ``executionBackend.slug``. The FK is
filled in eagerly (best-effort) when an example is assigned, but an example can
be uploaded/assigned *before* its execution backend is registered, so the FK is
frequently NULL and is never re-resolved on its own. Reading it directly (as the
upload + test-run paths used to) means a perfectly valid content can't be tested
just because the service was registered after the assignment.

This resolver fixes that: prefer the cached FK, otherwise resolve by the
example's slug, and backfill the FK so the next call is O(1). It returns None
only when the content genuinely has no example/slug or no matching enabled
service exists yet — so "create the content / upload the example before the
service" keeps working, and it "just works" the moment the service appears.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from computor_backend.model.course import CourseContent
from computor_backend.model.deployment import CourseContentDeployment
from computor_backend.model.example import ExampleVersion
from computor_backend.model.service import Service

logger = logging.getLogger(__name__)


def _usable(service: Optional[Service]) -> bool:
    return bool(service and service.enabled and service.archived_at is None)


def resolve_testing_service(course_content: CourseContent, db: Session) -> Optional[Service]:
    """Resolve the testing service for a content (lazy + self-healing).

    Order:
      1. the cached ``testing_service_id`` FK, when it still points at a usable
         (enabled, non-archived) service;
      2. otherwise the service whose ``slug`` equals the deployed example
         version's ``executionBackend.slug``;
      3. on a fresh resolution, backfill the FK (on the content, and on the
         example version) so later calls take the fast path and the column
         reflects reality.

    Returns None when the content has no example deployment / executionBackend
    slug, or no enabled service matches that slug yet.
    """
    # 1. Cached FK fast-path.
    if course_content.testing_service_id:
        cached = (
            db.query(Service)
            .filter(Service.id == course_content.testing_service_id)
            .first()
        )
        if _usable(cached):
            return cached
        # Stale FK (service disabled/removed) → fall through and re-resolve.

    # 2. Resolve by the deployed example version's executionBackend slug.
    deployment = (
        db.query(CourseContentDeployment)
        .filter(CourseContentDeployment.course_content_id == course_content.id)
        .first()
    )
    if deployment is None or deployment.example_version_id is None:
        return None

    example_version = (
        db.query(ExampleVersion)
        .filter(ExampleVersion.id == deployment.example_version_id)
        .first()
    )
    slug = example_version.get_execution_backend_slug() if example_version else None
    if not slug:
        return None

    service = (
        db.query(Service)
        .filter(
            Service.slug == slug,
            Service.enabled.is_(True),
            Service.archived_at.is_(None),
        )
        .first()
    )
    if service is None:
        return None

    # 3. Self-heal: cache the resolution. The caller's transaction persists it;
    #    if the caller doesn't commit, correctness still holds (re-resolved next
    #    time), we just don't get the O(1) fast path.
    course_content.testing_service_id = service.id
    if example_version is not None and example_version.testing_service_id != service.id:
        example_version.testing_service_id = service.id
    logger.info(
        "Resolved testing service '%s' for course content %s by executionBackend slug "
        "(backfilled testing_service_id)",
        slug, course_content.id,
    )
    return service
