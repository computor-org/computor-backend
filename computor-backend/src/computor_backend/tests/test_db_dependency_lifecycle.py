"""The request DB session must commit and close before the response goes out.

FastAPI >= 0.118 runs the exit code of ``yield`` dependencies *after* the
response is sent unless the dependency is declared with ``scope="function"``.
For ``get_db`` that would mean: a failing commit after a 200 was already sent
(and after background tasks ran), and a pooled connection held for the whole
duration of a streaming download. The app therefore declares every
``Depends(get_db, ...)`` with ``scope="function"`` — the lifecycle it had on
FastAPI 0.109.

The behavioural probes below run the real ``get_db`` against SQLite; the
control cases show the probes do detect the post-response lifecycle.
"""

import pytest
from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from computor_backend import database
from computor_backend.database import get_db

Base = declarative_base()


class Row(Base):
    __tablename__ = "lifecycle_row"
    id = Column(Integer, primary_key=True)


@pytest.fixture
def lifecycle_engine(monkeypatch, tmp_path):
    eng = create_engine(
        f"sqlite:///{tmp_path / 'lifecycle.db'}",
        poolclass=QueuePool,
        pool_size=2,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(Row.__table__.insert().values(id=1))
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=eng))
    return eng


def _app(engine, scope):
    app = FastAPI()
    ran = {"task": False, "checked_out_while_streaming": None}

    @app.post("/conflict")
    def conflict(tasks: BackgroundTasks, db=Depends(get_db, scope=scope)):
        db.add(Row(id=1))  # duplicate PK: fails only at the deferred commit
        tasks.add_task(lambda: ran.__setitem__("task", True))
        return {"ok": True}

    @app.get("/stream")
    def stream(db=Depends(get_db, scope=scope)):
        db.query(Row).count()  # check a connection out of the pool

        def body():
            ran["checked_out_while_streaming"] = engine.pool.checkedout()
            yield b"payload"

        return StreamingResponse(body())

    return app, ran


def test_deferred_commit_failure_is_500_and_skips_background_task(lifecycle_engine):
    app, ran = _app(lifecycle_engine, "function")
    client = TestClient(app, raise_server_exceptions=False)
    assert client.post("/conflict").status_code == 500
    assert ran["task"] is False


def test_streaming_response_does_not_hold_a_pool_connection(lifecycle_engine):
    app, ran = _app(lifecycle_engine, "function")
    assert TestClient(app).get("/stream").content == b"payload"
    assert ran["checked_out_while_streaming"] == 0


def test_control_request_scope_reports_success_before_commit(lifecycle_engine):
    """Oracle check: the default scope shows exactly the reviewed defect."""
    app, ran = _app(lifecycle_engine, None)
    client = TestClient(app, raise_server_exceptions=False)
    assert client.post("/conflict").status_code == 200
    assert ran["task"] is True
    client.get("/stream")
    assert ran["checked_out_while_streaming"] == 1


def _dependants(routes):
    for r in routes:
        inner = getattr(r, "original_router", None)
        if inner is not None:
            yield from _dependants(inner.routes)
        elif getattr(r, "dependant", None) is not None:
            yield r.path, r.dependant


def _get_db_scopes(dependant):
    for sub in dependant.dependencies:
        if sub.call is get_db:
            yield sub.scope
        yield from _get_db_scopes(sub)


def test_every_app_route_uses_function_scoped_get_db():
    from computor_backend.server import app

    checked, wrong = 0, []
    for path, dep in _dependants(app.routes):
        for scope in _get_db_scopes(dep):
            checked += 1
            if scope != "function":
                wrong.append(path)
    assert checked > 100
    assert not wrong, f"routes with request-scoped get_db: {sorted(set(wrong))}"
