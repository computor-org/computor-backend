"""Behaviour of the coder worker's restricted DB role on a real PostgreSQL.

Needs a disposable PostgreSQL (16) superuser DSN in COMPUTOR_TEST_PG_ADMIN_DSN,
e.g. postgresql://owner:pw@127.0.0.1:55437/postgres; skipped otherwise. Each
test gets a fresh database and role name.
"""

import os
import uuid

import pytest

psycopg2 = pytest.importorskip("psycopg2")
from psycopg2 import errors, sql  # noqa: E402

from computor_backend.scripts.ensure_coder_worker_db_role import (  # noqa: E402
    ensure_role,
    role_ready,
)

ADMIN_DSN = os.environ.get("COMPUTOR_TEST_PG_ADMIN_DSN")
pytestmark = pytest.mark.skipif(not ADMIN_DSN, reason="COMPUTOR_TEST_PG_ADMIN_DSN not set")

UID = "0232de59-e05d-4bc2-898f-b879c06abcde"
PASSWORD = "worker-pw"


def _connect(dbname=None, user=None, password=None):
    kwargs = {}
    if dbname:
        kwargs["dbname"] = dbname
    if user:
        kwargs["user"] = user
        kwargs["password"] = password
    return psycopg2.connect(ADMIN_DSN, **kwargs)


@pytest.fixture
def env():
    suffix = uuid.uuid4().hex[:8]
    db, role = f"rt_{suffix}", f"rt_worker_{suffix}"
    admin = _connect()
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db)))
    owner = _connect(db)
    with owner.cursor() as cur:
        cur.execute(
            'CREATE TABLE "user" (id text PRIMARY KEY, email text,'
            " workspace_app_key_version integer)"
        )
        cur.execute("CREATE TABLE api_token (id serial PRIMARY KEY, token_hash text)")
        cur.execute("INSERT INTO \"user\" VALUES (%s, 'a@example.org', 3)", (UID,))
        cur.execute("INSERT INTO api_token (token_hash) VALUES ('secret-hash')")
        # Legacy (pre-PG15) default: PUBLIC may create in schema public.
        cur.execute("GRANT CREATE ON SCHEMA public TO PUBLIC")
    owner.commit()
    assert ensure_role(owner, role, PASSWORD, db) is not None
    yield {"db": db, "role": role, "owner": owner}
    owner.close()
    with admin.cursor() as cur:
        cur.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(db)))
        cur.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))
    admin.close()


def _worker(env):
    conn = _connect(env["db"], env["role"], PASSWORD)
    conn.autocommit = True
    return conn


def _denied(conn, statement, exc=errors.InsufficientPrivilege):
    with conn.cursor() as cur, pytest.raises(exc):
        cur.execute(statement)


def test_worker_reads_only_its_two_columns(env):
    conn = _worker(env)
    with conn.cursor() as cur:
        cur.execute('SELECT workspace_app_key_version FROM "user" WHERE id = %s', (UID,))
        assert cur.fetchone() == (3,)
    _denied(conn, 'SELECT email FROM "user"')
    _denied(conn, "SELECT token_hash FROM api_token")
    assert role_ready(env["owner"], env["role"])


def test_writes_denied_even_with_read_only_switched_off(env):
    conn = _worker(env)
    with conn.cursor() as cur:
        cur.execute("SET default_transaction_read_only = off")
    _denied(conn, "UPDATE \"user\" SET workspace_app_key_version = 9")
    _denied(conn, "CREATE TABLE public.evil (i int)")
    _denied(conn, "CREATE TEMP TABLE evil (i int)")
    _denied(conn, "SELECT lo_create(0)")
    _denied(conn, "SELECT lo_from_bytea(0, 'x')")


def test_rerun_removes_memberships_ownership_and_stray_grants(env):
    owner, role, db = env["owner"], env["role"], env["db"]
    r = sql.Identifier(role)
    with owner.cursor() as cur:
        cur.execute(sql.SQL("GRANT pg_read_all_data TO {}").format(r))
        cur.execute(sql.SQL("GRANT SELECT ON api_token TO {}").format(r))
        cur.execute("CREATE TABLE owned_by_worker (i int)")
        cur.execute(sql.SQL("ALTER TABLE owned_by_worker OWNER TO {}").format(r))
    owner.commit()
    ensure_role(owner, role, PASSWORD, db)
    conn = _worker(env)
    with conn.cursor() as cur:  # prove the grants, not the read-only default
        cur.execute("SET default_transaction_read_only = off")
    _denied(conn, "SET ROLE pg_read_all_data")
    _denied(conn, "SELECT token_hash FROM api_token")
    _denied(conn, "INSERT INTO owned_by_worker VALUES (1)")
    with owner.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM pg_class c JOIN pg_roles o ON o.oid = c.relowner"
            " WHERE o.rolname = %s",
            (role,),
        )
        assert cur.fetchone() == (0,)
    owner.commit()


def test_password_rotation_and_app_owner_unaffected(env):
    owner, role, db = env["owner"], env["role"], env["db"]
    ensure_role(owner, role, "rotated", db)
    with pytest.raises(psycopg2.OperationalError):
        _connect(db, role, PASSWORD)
    _connect(db, role, "rotated").close()
    with owner.cursor() as cur:  # owner still creates tables and large objects
        cur.execute("CREATE TABLE owner_ok (i int)")
        cur.execute("SELECT lo_create(0)")
    owner.rollback()
