"""Real request failures must not expose private content to framework logs."""
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from computor_backend.api.public_luna import LunaRequest
from computor_backend.exceptions import register_exception_handlers
from computor_backend.exceptions.exceptions import InternalServerException
from computor_backend.public_luna_privacy import PublicLunaPrivacyMiddleware

SENTINEL = "private-learner-text-do-not-log"


def client():
    app = FastAPI(root_path="/api")
    register_exception_handlers(app)
    app.add_middleware(PublicLunaPrivacyMiddleware)

    @app.post("/public-luna/requests")
    def submit(body: LunaRequest):
        return {"state": "accepted"}

    @app.get("/public-luna/unexpected")
    def unexpected():
        raise RuntimeError(SENTINEL)

    @app.get("/public-luna/structured")
    def structured():
        raise InternalServerException(detail=SENTINEL, context={"answer": SENTINEL})

    return TestClient(app, raise_server_exceptions=True)


def assert_private(caplog):
    assert SENTINEL not in caplog.text
    assert SENTINEL not in json.dumps([record.__dict__ for record in caplog.records], default=str)
    assert all(record.exc_info is None for record in caplog.records)


def test_unknown_json_field_name_is_not_logged(caplog):
    response = client().post("/public-luna/requests", json={
        "course_content_id": "00000000-0000-0000-0000-000000000001",
        "question": "A synthetic question", SENTINEL: SENTINEL,
    })
    assert response.status_code == 400
    assert response.json() == {"message": "Invalid Luna request"}
    assert_private(caplog)


def test_unexpected_error_is_contained_before_asgi_server_logging(caplog):
    # raise_server_exceptions=True proves that the original exception does not
    # escape to the server's error logger, rather than only hiding its response.
    response = client().get("/public-luna/unexpected")
    assert response.status_code == 500
    assert response.json() == {"message": "Luna is temporarily unavailable"}
    assert_private(caplog)


def test_structured_error_context_and_traceback_are_not_logged(caplog):
    response = client().get("/public-luna/structured")
    assert response.status_code == 500
    assert_private(caplog)
