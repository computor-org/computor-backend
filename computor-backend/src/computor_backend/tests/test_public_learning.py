import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from computor_backend.api.public_catalog import public_catalog_router
from computor_backend.business_logic.public_learning import (
    available_description_languages,
    description_files,
    select_description_file,
    validate_public_asset_path,
)
from computor_backend.exceptions import NotFoundException

pytestmark = pytest.mark.unit


def test_learning_metadata_is_runtime_and_provenance_not_course_navigation():
    app = FastAPI()
    app.include_router(public_catalog_router)
    client = TestClient(app)

    result = client.get("/public/learning")

    assert result.status_code == 200
    body = result.json()
    assert set(body) == {
        "desktop_extension_url",
        "codespaces_url",
        "guide_url",
        "source_url",
        "server_execution",
    }
    assert body["server_execution"] == "authenticated"
    assert body["guide_url"] == "/learn"
    assert body["source_url"] == "https://github.com/computor-org/data-science-python"
    assert "courses" not in body
    assert "manifest_url" not in result.text
    assert "examples_url" not in result.text
    assert result.headers["cache-control"] == "public, max-age=300"

    for method in ["post", "put", "patch", "delete"]:
        assert getattr(client, method)("/public/learning").status_code == 405


def test_untrusted_query_cannot_select_repository_or_private_file():
    app = FastAPI()
    app.include_router(public_catalog_router)
    result = TestClient(app).get(
        "/public/learning",
        params={
            "file": "../../.env",
            "url": "http://169.254.169.254/metadata",
            "user_id": "synthetic-other-user",
        },
    )
    assert result.status_code == 200
    assert "metadata" not in result.text
    assert ".env" not in result.text
    assert "synthetic-other-user" not in result.text


def test_description_files_only_expose_top_level_readmes_and_languages():
    names = [
        "versions/v1/content/index_de.md",
        "versions/v1/content/index_en.md",
        "versions/v1/content/README_en.md",
        "versions/v1/content/mediaFiles/figure.png",
        "versions/v1/content/localTests/secret.md",
        "versions/v1/test.yaml",
    ]

    files = description_files(names, "versions/v1")

    assert files == {
        "de": "versions/v1/content/index_de.md",
        "en": "versions/v1/content/index_en.md",
    }
    assert available_description_languages(files) == ["de", "en"]
    assert select_description_file(files, "en", "de") == (
        "en",
        "versions/v1/content/index_en.md",
    )
    assert select_description_file(files, None, "de") == (
        "de",
        "versions/v1/content/index_de.md",
    )


def test_public_assets_are_restricted_to_mediafiles():
    assert validate_public_asset_path("mediaFiles/plot.png") == "mediaFiles/plot.png"
    assert (
        validate_public_asset_path("/mediaFiles/figures/plot.svg")
        == "mediaFiles/figures/plot.svg"
    )

    for value in [
        "../test.yaml",
        "mediaFiles/../test.yaml",
        "localTests/solution.py",
        "README.md",
        "mediaFiles",
    ]:
        with pytest.raises(NotFoundException):
            validate_public_asset_path(value)
