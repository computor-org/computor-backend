"""Database fixtures for the integration stack.

Exposes a session-scoped psycopg connection at the stack's published Postgres
port. Used for seed operations the admin API can't do (today: `POST /courses`
requires `organization_id`, which isn't in the `CourseCreate` DTO — this is a
backend bug/gap tracked under issue #106). Also handy for later assertion
fixtures that need to look at raw rows.
"""

from __future__ import annotations

import os
from typing import Iterator

import psycopg
import pytest


def _dsn() -> str:
    host = "localhost"
    port = os.environ.get("IT_POSTGRES_PORT", "15432")
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    db = os.environ["POSTGRES_DB"]
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture(scope="session")
def db_conn() -> Iterator[psycopg.Connection]:
    """Session-scoped autocommit connection to the integration Postgres.

    Autocommit so seed inserts become visible to the API immediately and so
    tests running in parallel don't hold long transactions.
    """
    with psycopg.connect(_dsn(), autocommit=True) as conn:
        yield conn
