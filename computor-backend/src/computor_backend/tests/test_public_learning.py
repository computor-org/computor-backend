import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from computor_backend.api.public_catalog import public_catalog_router

pytestmark = pytest.mark.unit


def test_anonymous_learning_metadata_needs_no_database_and_carries_no_execution_capability():
    app = FastAPI()
    app.include_router(public_catalog_router)
    client = TestClient(app)
    result = client.get("/public/learning")
    assert result.status_code == 200
    body = result.json()
    assert len(body["courses"]) == 3
    assert sum(course["exercises"] for course in body["courses"]) == 70
    assert body["server_execution"] == "authenticated"
    assert body["codespaces_ai"] == "external-provider-byok"
    assert result.headers["cache-control"] == "public, max-age=300"
    for course in body["courses"]:
        assert set(course) == {"slug", "title", "exercises", "languages", "manifest_url", "examples_url", "license"}
        assert course["manifest_url"].startswith("https://github.com/computor-org/data-science-python/blob/main/courses/")
    for method in ["post", "put", "patch", "delete"]:
        assert getattr(client, method)("/public/learning").status_code == 405


def test_untrusted_query_cannot_select_another_repository_or_private_file():
    app = FastAPI()
    app.include_router(public_catalog_router)
    result = TestClient(app).get("/public/learning", params={
        "file": "../../.env", "url": "http://169.254.169.254/metadata", "user_id": "synthetic-other-user"})
    assert result.status_code == 200
    assert "metadata" not in result.text
    assert ".env" not in result.text
    assert "synthetic-other-user" not in result.text
