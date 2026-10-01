"""Real PostgreSQL oracles for public grading queue admission and recovery.

Set PUBLIC_TESTING_TEST_DATABASE_URL to an isolated disposable PostgreSQL DB.
The fixture owns only its two probe tables and leaves production data untouched.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import Column, Integer, create_engine, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, sessionmaker

from computor_backend.business_logic.public_testing_admission import (
    commit_admitted_result,
    release_definitive_start_failure,
    release_for_result,
    require_public_result_writer,
)
from computor_backend.business_logic.result_reconciler import _release_terminal_reservations
from computor_backend.exceptions import ForbiddenException, RateLimitException
from computor_backend.model.public_grading_reservation import PublicGradingReservation
from computor_backend.tasks.temporal_executor import TaskNotFoundError, TaskRegistrationError
from computor_types.tasks import TaskStatus

ProbeBase = declarative_base()


class ProbeResult(ProbeBase):
    __tablename__ = "public_grading_probe_result"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    status = Column(Integer, nullable=False, default=4)


@pytest.fixture
def sessions(monkeypatch):
    url = os.environ.get("PUBLIC_TESTING_TEST_DATABASE_URL")
    if not url:
        pytest.skip("requires isolated PUBLIC_TESTING_TEST_DATABASE_URL")
    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "true")
    monkeypatch.setenv("PUBLIC_TEST_MAX_INFLIGHT", "3")
    engine = create_engine(url, pool_size=8, max_overflow=0)
    PublicGradingReservation.__table__.create(engine)
    ProbeBase.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    ProbeBase.metadata.drop_all(engine)
    PublicGradingReservation.__table__.drop(engine)
    engine.dispose()


def _admit(factory, workflow_id):
    with factory() as db:
        result = ProbeResult()
        try:
            commit_admitted_result(db, result, workflow_id)
        except Exception:
            db.rollback()
            raise
        return result.id


def _occupied(factory):
    with factory() as db:
        return db.query(func.count(PublicGradingReservation.workflow_id)).filter(
            PublicGradingReservation.released_at.is_(None)).scalar()


def test_parallel_limit_survives_restart_and_forged_terminal_or_cascade(sessions):
    # Six independent API sessions race a cap of three. A process-local
    # semaphore or a count without the transaction lock admits too many.
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(_admit, sessions, f"student-testing-{i}") for i in range(6)]
        successes = []
        rejections = 0
        for future in futures:
            try:
                successes.append(future.result())
            except RateLimitException:
                rejections += 1
    assert len(successes) == 3
    assert rejections == 3
    assert _occupied(sessions) == 3

    # Forging FINISHED and deleting its Result cannot free an active workflow.
    with sessions() as db:
        result = db.query(ProbeResult).filter(ProbeResult.id == successes[0]).one()
        result.status = 0
        db.delete(result)
        db.commit()
    assert _occupied(sessions) == 3

    # A new engine/session models an API restart; reservations are still there.
    sessions.kw["bind"].dispose()
    with pytest.raises(RateLimitException):
        _admit(sessions, "student-testing-after-restart")


def test_only_proven_terminal_or_local_pre_rpc_failure_releases(sessions):
    ids = [_admit(sessions, f"student-testing-{i}") for i in range(3)]
    with sessions() as db:
        assert release_definitive_start_failure(
            db, "student-testing-0", TimeoutError("Temporal reply lost")) == 0
        db.commit()
    assert _occupied(sessions) == 3
    with pytest.raises(RateLimitException):
        _admit(sessions, "student-testing-blocked")

    with sessions() as db:
        assert release_definitive_start_failure(
            db, "student-testing-0", TaskRegistrationError("unknown task")) == 1
        db.commit()
    assert _admit(sessions, "student-testing-next")

    with sessions() as db:
        assert release_for_result(db, ids[1]) == 1
        db.commit()
    assert _admit(sessions, "student-testing-after-trusted-callback")


@pytest.mark.asyncio
async def test_reconciler_uses_temporal_terminal_not_age_or_missing(sessions, monkeypatch):
    import computor_backend.tasks as tasks

    for i in range(3):
        _admit(sessions, f"student-testing-{i}")

    class Executor:
        async def get_task_status(self, workflow_id):
            if workflow_id.endswith("-0"):
                return SimpleNamespace(status=TaskStatus.FINISHED)
            if workflow_id.endswith("-1"):
                return SimpleNamespace(status=TaskStatus.STARTED)
            raise TaskNotFoundError(workflow_id)

    monkeypatch.setattr(tasks, "get_task_executor", lambda: Executor())
    with sessions() as db:
        assert await _release_terminal_reservations(db, datetime.max.replace(tzinfo=timezone.utc)) == 1
    assert _occupied(sessions) == 2


def test_public_writers_are_trusted_only(monkeypatch):
    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "true")
    with pytest.raises(ForbiddenException):
        require_public_result_writer(SimpleNamespace(is_service=False, is_admin=False))
    require_public_result_writer(SimpleNamespace(is_service=True, is_admin=False))
    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "false")
    require_public_result_writer(SimpleNamespace(is_service=False, is_admin=False))


@pytest.mark.asyncio
async def test_public_redis_failure_does_not_admit(monkeypatch):
    from computor_backend.api.tests import check_user_rate_limit

    class FailedRedis:
        async def get(self, _key):
            raise ConnectionError("redis unavailable")

    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "true")
    with pytest.raises(RateLimitException):
        await check_user_rate_limit("synthetic-user", FailedRedis())
    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "false")
    assert await check_user_rate_limit("synthetic-user", FailedRedis()) is False
