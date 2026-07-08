"""Characterization tests for the single-unit-of-work transaction model.

Repositories flush (not commit); the surrounding ``get_db_session`` commits
once. Cache invalidation is deferred to the session's ``after_commit`` event,
so a rolled-back write never evicts a live cache entry. These run against the
live dev Postgres and roll all data back.
"""
import os
import uuid

import pytest
from sqlalchemy_utils import Ltree

from computor_backend.database import SessionLocal, register_post_commit
from computor_backend.model.organization import Organization
from computor_backend.repositories.organization import OrganizationRepository


def _pg_reachable() -> bool:
    try:
        s = SessionLocal()
        s.execute(__import__("sqlalchemy").text("SELECT 1"))
        s.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _pg_reachable(), reason="Postgres not reachable")


def _new_org() -> Organization:
    suffix = uuid.uuid4().hex[:10]
    return Organization(
        title="UoW Test Org",
        organization_type="organization",
        path=Ltree(f"uow_{suffix}"),
        properties={},
    )


def test_repo_create_flushes_not_commits_and_commit_persists():
    """A repo create is visible in-session after flush, and persists on commit."""
    org = _new_org()
    org_id = None
    session = SessionLocal()
    try:
        repo = OrganizationRepository(session)
        created = repo.create(org)
        org_id = created.id
        # Flushed: server defaults populated, visible in THIS session.
        assert org_id is not None
        assert session.query(Organization).filter_by(id=org_id).first() is not None
        session.commit()
    finally:
        session.close()

    # A fresh session sees it only because we committed.
    check = SessionLocal()
    try:
        assert check.query(Organization).filter_by(id=org_id).first() is not None
        # cleanup
        check.query(Organization).filter_by(id=org_id).delete()
        check.commit()
    finally:
        check.close()


def test_repo_create_rolled_back_is_not_persisted():
    """Without a commit, a flushed repo create does not persist (single UoW)."""
    org = _new_org()
    session = SessionLocal()
    org_id = None
    try:
        repo = OrganizationRepository(session)
        org_id = repo.create(org).id
        session.rollback()
    finally:
        session.close()

    check = SessionLocal()
    try:
        assert check.query(Organization).filter_by(id=org_id).first() is None
    finally:
        check.close()


def test_post_commit_callback_fires_on_commit():
    fired = []
    session = SessionLocal()
    try:
        session.execute(__import__("sqlalchemy").text("SELECT 1"))  # open a txn
        register_post_commit(session, lambda: fired.append("commit"))
        assert fired == []  # not yet
        session.commit()
        assert fired == ["commit"]
    finally:
        session.close()


def test_post_commit_callback_dropped_on_rollback():
    fired = []
    session = SessionLocal()
    try:
        session.execute(__import__("sqlalchemy").text("SELECT 1"))
        register_post_commit(session, lambda: fired.append("commit"))
        session.rollback()
        session.commit()  # nothing queued anymore
        assert fired == []
    finally:
        session.close()
