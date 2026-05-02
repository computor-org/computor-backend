"""Regression test for the UUID column type.

SQLAlchemy 1.4's psycopg2 dialect ships ``_PGUUID`` whose
``bind_processor`` calls ``uuid.UUID(value)`` on every INSERT
parameter. The stdlib constructor does ``hex.replace('urn:', '')``
which raises ``AttributeError: 'UUID' object has no attribute
'replace'`` whenever the value is already a ``uuid.UUID`` instance —
e.g. a FastAPI ``UUID`` path parameter handed to the ORM as a foreign
key on INSERT. ``custom_types.UUID`` wraps the dialect type in a
``TypeDecorator`` that pre-stringifies UUID instances so the
underlying processor only ever sees a string.
"""

from __future__ import annotations

import os
import uuid

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from computor_backend.custom_types import Ltree
from computor_backend.model.organization import Organization


def _pg_url() -> str:
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    db = os.environ.get("POSTGRES_DB")
    if not (user and password and db):
        pytest.skip("postgres test environment not configured")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture
def pg_session():
    engine = create_engine(_pg_url(), future=True)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()


@pytest.mark.integration
def test_uuid_column_accepts_uuid_instance_on_insert(pg_session):
    # FastAPI path parameters declared as ``UUID`` arrive at the ORM as
    # ``uuid.UUID`` objects. Without the TypeDecorator the flush below
    # raises ``StatementError: 'UUID' object has no attribute
    # 'replace'`` from inside SQLAlchemy's psycopg2 bind processor.
    suffix = uuid.uuid4().hex[:8]
    org = Organization(
        id=uuid.uuid4(),
        path=Ltree(f"itest_{suffix}"),
        title=f"Issue-244 Org {suffix}",
        organization_type="community",
        properties={},
    )
    pg_session.add(org)
    pg_session.flush()
