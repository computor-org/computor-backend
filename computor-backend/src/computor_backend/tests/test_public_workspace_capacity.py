"""Public cap behavior across concurrent requests, crash, and stale Coder views."""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from computor_backend.business_logic import public_workspace_capacity as capacity
from computor_backend.coder.client import CoderClient
from computor_backend.coder.exceptions import CoderAPIError
from computor_backend.coder.schemas import CoderWorkspace, WorkspaceBuildStatus
from computor_backend.exceptions import RateLimitException, ServiceUnavailableException


def workspace(owner, name, build, status=WorkspaceBuildStatus.SUCCEEDED):
    return CoderWorkspace(
        id=f"{owner}-{name}", name=name, owner_id=owner, owner_name=owner,
        template_id="template", template_name="vscode-workspace",
        latest_build_id=build,
        latest_build_transition="stop" if status == WorkspaceBuildStatus.STOPPED else "start",
        latest_build_status=status,
    )


class Store:
    """Transaction oracle: only commits persist; one advisory owner at a time."""

    def __init__(self):
        self.rows = {}
        self.owner = None

    def session(self):
        return Session(self)


class Session:
    def __init__(self, store):
        self.store = store
        self.changes = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.rollback()

    def execute(self, sql, params=None):
        query = str(sql)
        params = params or {}
        if "pg_try_advisory_xact_lock" in query:
            if self.store.owner is None:
                self.store.owner = self
            return SimpleNamespace(scalar_one=lambda: self.store.owner is self)
        assert self.store.owner is self
        if query.startswith("SELECT owner_name"):
            rows = {**self.store.rows, **self.changes}
            return SimpleNamespace(all=lambda: [
                SimpleNamespace(owner_name=k[0], workspace_name=k[1], baseline_build_id=v)
                for k, v in rows.items() if v is not None
            ])
        key = (params["owner"], params["workspace"])
        if query.startswith("DELETE"):
            self.changes[key] = None
        elif query.startswith("INSERT"):
            self.changes[key] = params["baseline"]
        else:
            raise AssertionError(query)
        return SimpleNamespace()

    def commit(self):
        for key, value in self.changes.items():
            if value is None:
                self.store.rows.pop(key, None)
            else:
                self.store.rows[key] = value
        self.rollback()

    def rollback(self):
        self.changes = {}
        if self.store.owner is self:
            self.store.owner = None


@pytest.fixture
def public(monkeypatch):
    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "true")
    monkeypatch.setenv("CODER_MAX_RUNNING_WORKSPACES", "1")
    store = Store()
    monkeypatch.setattr(capacity, "SessionLocal", store.session)
    return store


def coder_with_fleet(initial=None):
    coder = SimpleNamespace(workspaces=list(initial or []))

    async def inventory(max_items):
        assert max_items == 10000
        await asyncio.sleep(0.02)
        return list(coder.workspaces)

    coder.list_all_workspaces_complete = inventory
    return coder


@pytest.mark.asyncio
async def test_concurrent_provisions_survive_restart_and_stale_inventory(public):
    coder = coder_with_fleet()
    results = await asyncio.gather(
        capacity.reserve_public_container(coder, "alice", "vscode"),
        capacity.reserve_public_container(coder, "bob", "vscode"),
        return_exceptions=True,
    )
    assert sum(result is None for result in results) == 1
    assert sum(isinstance(result, RateLimitException) for result in results) == 1
    assert len(public.rows) == 1

    # The process can disappear before Coder receives the build; a new API
    # session still sees the committed row and cannot over-admit.
    owner = next(iter(public.rows))[0]
    with pytest.raises(RateLimitException):
        await capacity.reserve_public_container(coder, "charlie", "vscode")
    assert len(public.rows) == 1

    # The old stopped build cannot clear a reservation for a new start.
    public.rows[(owner, "vscode")] = "old"
    coder.workspaces = [workspace(owner, "vscode", "old", WorkspaceBuildStatus.STOPPED)]
    with pytest.raises(RateLimitException):
        await capacity.reserve_public_container(coder, "charlie", "vscode")
    assert len(public.rows) == 1

    coder.workspaces = [workspace(owner, "vscode", "new")]
    with pytest.raises(RateLimitException):
        await capacity.reserve_public_container(coder, "charlie", "vscode")
    assert public.rows == {}
    await capacity.reserve_public_container(coder, owner, "vscode")  # active idempotence
    assert public.rows == {}
    coder.workspaces = [workspace(owner, "vscode", "stopped", WorkspaceBuildStatus.STOPPED)]
    await capacity.reserve_public_container(coder, "charlie", "vscode")
    assert public.rows == {("charlie", "vscode"): "-"}


@pytest.mark.asyncio
async def test_failed_inventory_and_lost_lock_fail_closed(public):
    coder = coder_with_fleet()
    async def fail_inventory(max_items):
        raise CoderAPIError("inventory incomplete")
    coder.list_all_workspaces_complete = fail_inventory
    with pytest.raises(CoderAPIError):
        await capacity.reserve_public_container(coder, "alice", "vscode")
    assert public.rows == {}
    assert public.owner is None

    public.owner = object()
    with pytest.raises(ServiceUnavailableException, match="busy"):
        await capacity.reserve_public_container(coder, "alice", "vscode")
    assert public.rows == {}


@pytest.mark.asyncio
async def test_coder_inventory_requires_full_count(monkeypatch):
    client = CoderClient(settings=SimpleNamespace())
    client._request = AsyncMock(return_value=SimpleNamespace(json=lambda: {
        "count": 2, "workspaces": []
    }))
    with pytest.raises(CoderAPIError, match="incomplete"):
        await client.list_all_workspaces_complete()
    assert client._request.await_count == 1


@pytest.mark.parametrize("raw", ["", "0", "-1", "NaN", "inf", "10001"])
def test_public_requires_finite_positive_config(monkeypatch, raw):
    monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "true")
    monkeypatch.setenv("CODER_MAX_RUNNING_WORKSPACES", raw)
    with pytest.raises(ServiceUnavailableException):
        capacity.required_public_container_limit()


def test_private_deployment_has_no_new_cap(monkeypatch):
    monkeypatch.delenv("COMPUTOR_PUBLIC_DEPLOYMENT", raising=False)
    monkeypatch.delenv("CODER_MAX_RUNNING_WORKSPACES", raising=False)
    assert capacity.required_public_container_limit() is None


@pytest.mark.asyncio
async def test_real_postgres_serializes_and_persists_reservations(monkeypatch):
    """Synthetic Postgres oracle, isolated by a random schema in CI."""
    url = os.environ.get("PUBLIC_WORKSPACE_TEST_DATABASE_URL")
    if not url:
        pytest.skip("set PUBLIC_WORKSPACE_TEST_DATABASE_URL to disposable Postgres")
    schema = "cap_" + uuid4().hex
    admin = create_engine(url)
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE TABLE public_workspace_reservation ("
                "owner_name text NOT NULL, workspace_name text NOT NULL, "
                "baseline_build_id text NOT NULL, "
                "PRIMARY KEY (owner_name, workspace_name))"
            ))
        monkeypatch.setenv("COMPUTOR_PUBLIC_DEPLOYMENT", "true")
        monkeypatch.setenv("CODER_MAX_RUNNING_WORKSPACES", "1")
        monkeypatch.setattr(capacity, "SessionLocal", sessionmaker(bind=engine))
        coder = coder_with_fleet()
        results = await asyncio.gather(
            capacity.reserve_public_container(coder, "alice", "vscode"),
            capacity.reserve_public_container(coder, "bob", "vscode"),
            return_exceptions=True,
        )
        assert sum(result is None for result in results) == 1
        assert sum(isinstance(result, RateLimitException) for result in results) == 1
        with engine.connect() as conn:  # a new session after the original request
            rows = conn.execute(text(
                "SELECT owner_name, workspace_name FROM public_workspace_reservation"
            )).all()
        assert len(rows) == 1
        with pytest.raises(RateLimitException):
            await capacity.reserve_public_container(coder, "charlie", "vscode")
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
