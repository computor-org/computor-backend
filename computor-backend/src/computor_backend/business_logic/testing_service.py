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


def _enabled_services(db: Session):
    return db.query(Service).filter(
        Service.enabled.is_(True),
        Service.archived_at.is_(None),
    )


def _config_str(service: Service, key: str) -> Optional[str]:
    config = service.config
    if not isinstance(config, dict):
        return None
    value = config.get(key)
    return value.strip().lower() if isinstance(value, str) and value.strip() else None


def resolve_service_for_execution_backend(
    db: Session, execution_backend: Optional[dict]
) -> Optional[Service]:
    """Resolve an ``executionBackend`` block to the Service that should run it.

    This is the single definition of the binding, used by the upload path, the
    assignment path and the test-run path.

    Order:

    1. **A pinned ``slug`` wins outright.** It names one specific runner and is
       honoured strictly — if that service is missing or disabled the answer is
       None, never "something else that looks similar". Silently substituting a
       different test runner is not a favour.
    2. Otherwise match on ``language`` — what the example actually needs. An
       exact ``version`` match is preferred; failing that, a runner for that
       language which declares no version at all (the generic one) is used.

    The language route is what makes examples portable: `language: octave` runs
    on any installation that has an octave runner, whereas a slug hardcodes one
    deployment's service name into the content.
    """
    if not isinstance(execution_backend, dict):
        return None

    slug = execution_backend.get("slug")
    if isinstance(slug, str) and slug.strip():
        service = _enabled_services(db).filter(Service.slug == slug.strip()).first()
        if service is None and execution_backend.get("language"):
            logger.info(
                "executionBackend pins slug %r which has no enabled service; NOT "
                "falling back to language %r — a pin selects one specific runner.",
                slug, execution_backend.get("language"),
            )
        return service

    language = execution_backend.get("language")
    if not isinstance(language, str) or not language.strip():
        return None
    language = language.strip().lower()

    candidates = [
        s for s in _enabled_services(db).all() if _config_str(s, "language") == language
    ]
    if not candidates:
        return None

    version = execution_backend.get("version")
    if version is not None and str(version).strip():
        wanted = str(version).strip().lower()
        exact = [s for s in candidates if _config_str(s, "language_version") == wanted]
        if exact:
            return exact[0]
        # No runner pinned to that version — fall back to a generic one for the
        # language (no language_version declared) rather than an arbitrary
        # differently-versioned runner.
        generic = [s for s in candidates if _config_str(s, "language_version") is None]
        if generic:
            logger.info(
                "No %s runner declares version %r; using the generic %s runner '%s'.",
                language, version, language, generic[0].slug,
            )
            return generic[0]
        logger.info(
            "No %s runner matches version %r (available: %s).",
            language, version,
            [_config_str(s, "language_version") for s in candidates],
        )
        return None

    return candidates[0]


def resolve_testing_service(course_content: CourseContent, db: Session) -> Optional[Service]:
    """Resolve the testing service for a content (lazy + self-healing).

    Order:
      1. the cached ``testing_service_id`` FK, when it still points at a usable
         (enabled, non-archived) service;
      2. otherwise ``resolve_service_for_execution_backend`` on the deployed
         example version's ``executionBackend`` (pinned slug, else language);
      3. on a fresh resolution, backfill the FK (on the content, and on the
         example version) so later calls take the fast path and the column
         reflects reality.

    Returns None when the content has no example deployment / executionBackend,
    or nothing enabled matches it yet.
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
    execution_backend = example_version.execution_backend if example_version else None
    service = resolve_service_for_execution_backend(db, execution_backend)
    if service is None:
        return None
    binding = (
        execution_backend.get("slug")
        or execution_backend.get("language")
    )

    # 3. Self-heal: cache the resolution. The caller's transaction persists it;
    #    if the caller doesn't commit, correctness still holds (re-resolved next
    #    time), we just don't get the O(1) fast path.
    course_content.testing_service_id = service.id
    if example_version is not None and example_version.testing_service_id != service.id:
        example_version.testing_service_id = service.id
    logger.info(
        "Resolved testing service '%s' for course content %s via executionBackend %r "
        "(backfilled testing_service_id)",
        service.slug, course_content.id, binding,
    )
    return service
