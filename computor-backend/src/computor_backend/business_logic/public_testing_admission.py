"""PostgreSQL-backed public grading admission; reservations have no expiry."""

import os

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from computor_backend.exceptions import ForbiddenException, RateLimitException
from computor_backend.model.public_grading_reservation import PublicGradingReservation


# Two fixed PostgreSQL advisory-lock keys, shared by every API replica.
_LOCK_NAMESPACE = 0x434F4D50
_LOCK_KEY = 0x54455354
_DEFAULT_LIMIT = 100


def public_test_limit() -> int | None:
    if os.environ.get("COMPUTOR_PUBLIC_DEPLOYMENT", "").strip().lower() != "true":
        return None
    raw = os.environ.get("PUBLIC_TEST_MAX_INFLIGHT", str(_DEFAULT_LIMIT))
    try:
        limit = int(raw)
    except ValueError as exc:
        raise RuntimeError("PUBLIC_TEST_MAX_INFLIGHT must be a positive integer") from exc
    if not 1 <= limit <= 100:
        raise RuntimeError("PUBLIC_TEST_MAX_INFLIGHT must be between 1 and 100")
    return limit


def require_public_result_writer(permissions) -> None:
    """Only trusted workers/admins may write grading records on a public site."""
    if public_test_limit() is not None and not (permissions.is_service or permissions.is_admin):
        raise ForbiddenException(detail="Only the testing service may update results")


def commit_admitted_result(db: Session, result, workflow_id: str) -> None:
    """Atomically count, reserve and commit a student-testing Result.

    The transaction advisory lock serializes concurrent admissions across API
    replicas. The reservation row survives API restarts and Result deletion;
    only a known terminal workflow or trusted result callback releases it.
    """
    limit = public_test_limit()
    if limit is not None:
        db.execute(text("SELECT pg_advisory_xact_lock(:namespace, :key)"),
                   {"namespace": _LOCK_NAMESPACE, "key": _LOCK_KEY})
        occupied = db.query(func.count(PublicGradingReservation.workflow_id)).filter(
            PublicGradingReservation.released_at.is_(None)
        ).scalar()
        if occupied >= limit:
            raise RateLimitException(
                error_code="RATE_003", detail="Testing is busy. Please try again shortly.",
                retry_after=30,
            )
    db.add(result)
    db.flush()
    if limit is not None:
        db.add(PublicGradingReservation(workflow_id=workflow_id, result_id=result.id))
    db.commit()


def release_for_result(db: Session, result_id) -> int:
    """Release after a trusted worker update or observed Temporal terminal state."""
    if public_test_limit() is None:
        return 0
    return db.query(PublicGradingReservation).filter(
        PublicGradingReservation.result_id == result_id,
        PublicGradingReservation.released_at.is_(None),
    ).update({PublicGradingReservation.released_at: func.now()}, synchronize_session=False)


def release_for_workflow(db: Session, workflow_id: str) -> int:
    if public_test_limit() is None:
        return 0
    return db.query(PublicGradingReservation).filter(
        PublicGradingReservation.workflow_id == workflow_id,
        PublicGradingReservation.released_at.is_(None),
    ).update({PublicGradingReservation.released_at: func.now()}, synchronize_session=False)


def release_definitive_start_failure(db: Session, workflow_id: str, error: Exception) -> int:
    """Release only a local registry rejection, before any Temporal RPC."""
    from computor_backend.tasks.temporal_executor import TaskRegistrationError

    if isinstance(error, TaskRegistrationError):
        return release_for_workflow(db, workflow_id)
    return 0
