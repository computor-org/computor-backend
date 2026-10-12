"""Students receive only released descriptions and their public static assets."""

import io
import zipfile
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql import operators

import computor_backend.business_logic.student_description as descriptions
from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.model.course import CourseContent
from computor_backend.model.deployment import DeploymentHistory
from computor_backend.permissions.principal import Principal

CONTENT_ID = "5ef06519-b515-4158-8039-f28e5da5eed4"
COURSE_ID = "01882d3f-4b95-4c75-9b16-d60a5b2d8f31"
RELEASED_VERSION = "5026f2c8-4e7e-4ae1-b0a4-8fcfd01b7a89"
PREFIX = "examples/repository/assignment/v1"


@pytest.fixture
def description(monkeypatch):
    content = SimpleNamespace(id=CONTENT_ID, course_id=COURSE_ID, archived_at=None)
    db = MagicMock()
    content_query = MagicMock()
    content_query.filter.return_value.first.return_value = content
    history = []

    def query(model):
        if model is CourseContent:
            return content_query
        assert model is DeploymentHistory
        history_query = MagicMock()
        filters = []
        ordering = []

        def filter_history(*criteria):
            filters.extend(criteria)
            return history_query

        def order_history(*criteria):
            ordering.extend(criteria)
            return history_query

        def first_history():
            rows = [row for row in history if all(
                str(getattr(row, clause.left.key)) == str(clause.right.value)
                for clause in filters
            )]
            for clause in reversed(ordering):
                rows.sort(
                    key=lambda row: getattr(row, clause.element.key),
                    reverse=clause.modifier is operators.desc_op,
                )
            return rows[0] if rows else None

        history_query.filter.side_effect = filter_history
        history_query.order_by.side_effect = order_history
        history_query.first.side_effect = first_history
        return history_query

    db.query.side_effect = query
    membership = MagicMock(return_value=SimpleNamespace(user_id="student"))
    visibility = MagicMock(return_value=True)
    monkeypatch.setattr(descriptions, "get_course_member_or_403", membership)
    monkeypatch.setattr(descriptions, "is_student_visible", visibility)

    deployment = SimpleNamespace(
        id="deployment-1",
        example_version_id=RELEASED_VERSION, deployed_at=datetime.now(timezone.utc),
        deployment_status="deployed",
    )
    deployment_repo = MagicMock()
    deployment_repo.find_latest_for_course_content.return_value = deployment
    deployment_factory = MagicMock(return_value=deployment_repo)
    monkeypatch.setattr(descriptions, "CourseContentDeploymentRepository", deployment_factory)

    repository = SimpleNamespace(source_type="minio", source_url="example-bucket/repository")
    version = SimpleNamespace(storage_path=PREFIX, example=SimpleNamespace(repository=repository))
    version_repo = MagicMock()
    version_repo.get_with_relationships.return_value = version
    version_factory = MagicMock(return_value=version_repo)
    monkeypatch.setattr(descriptions, "ExampleVersionRepository", version_factory)

    files = {f"{PREFIX}/content/index.md": b"# Assignment\nDo this exercise."}
    storage = SimpleNamespace(list_objects=AsyncMock(), download_file=AsyncMock())
    storage.list_objects.side_effect = lambda **_: [SimpleNamespace(object_name=name) for name in files]
    storage.download_file.side_effect = lambda *, object_key, bucket_name: files[object_key]
    return SimpleNamespace(
        permissions=Principal(user_id="student"), db=db, content=content,
        content_query=content_query, history=history,
        membership=membership, visibility=visibility, deployment=deployment,
        deployment_repo=deployment_repo, deployment_factory=deployment_factory,
        version=version, version_repo=version_repo, version_factory=version_factory,
        repository=repository, files=files, storage=storage,
    )


async def _download(ctx):
    return await descriptions.get_student_description(
        CONTENT_ID, ctx.permissions, ctx.db, ctx.storage
    )


async def _archive(response):
    chunks = [chunk async for chunk in response.body_iterator]
    return zipfile.ZipFile(io.BytesIO(b"".join(chunks)))


@pytest.mark.asyncio
@pytest.mark.parametrize("source_type", ["minio", "s3"])
async def test_downloads_current_released_description_as_private_zip(description, source_type):
    description.repository.source_type = source_type
    response = await _download(description)
    archive = await _archive(response)

    assert response.media_type == "application/zip"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["content-disposition"] == 'attachment; filename="assignment_description.zip"'
    assert archive.namelist() == ["index.md"]
    assert archive.read("index.md") == description.files[f"{PREFIX}/content/index.md"]
    description.db.query.assert_called_once_with(CourseContent)
    description.membership.assert_called_once_with(description.permissions, COURSE_ID, description.db)
    description.visibility.assert_called_once_with(description.db, description.content)
    description.deployment_factory.assert_called_once_with(description.db)
    description.version_factory.assert_called_once_with(description.db)
    description.version_repo.get_with_relationships.assert_called_once_with(RELEASED_VERSION)
    description.storage.list_objects.assert_awaited_once_with(
        bucket_name="example-bucket", prefix=f"{PREFIX}/content/"
    )


@pytest.mark.asyncio
async def test_zip_contains_localized_descriptions_and_safe_assets_but_no_authoring_data(description):
    public_files = {
        "index.md", "index_de.md", "index_en-US.md", "README.md", "readme_de_AT.md",
        "mediaFiles/illustration.png", "assets/data.csv", "images/diagram.svg",
        "assets/chapter/lecture.pdf",
    }
    private_files = {
        "solution.py", "test.yaml", "meta.yaml", "tests/check.py", "reference/answer.py",
        "assets/solution/answer.txt", "assets/tests/input.csv", "assets/.hidden/input.txt",
        "assets/solution.txt", "assets/reference_answer.csv", "assets/test_hidden.txt",
        "assets/run.py", "assets/script.js", "assets/page.html", ".env",
        "index_solution.md", "notes.md", "mediaFiles/../solution.txt",
        "mediaFiles/./image.png", "mediaFiles//image.png", "../index.md",
        "mediaFiles\\image.png",
    }
    description.files.clear()
    description.files.update({f"{PREFIX}/content/{name}": name.encode() for name in public_files | private_files})
    description.files.update({
        f"{PREFIX}/reference/index.md": b"secret answer",
        f"{PREFIX}-other/content/index.md": b"wrong version",
        f"{PREFIX}/content/": b"",
    })

    archive = await _archive(await _download(description))

    assert set(archive.namelist()) == public_files
    assert {call.kwargs["object_key"] for call in description.storage.download_file.await_args_list} == {
        f"{PREFIX}/content/{name}" for name in public_files
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("unavailable", ["missing", "archived", "hidden", "not-a-member"])
async def test_access_is_checked_before_reading_any_example_or_storage(description, unavailable):
    expected_exception = NotFoundException
    if unavailable == "missing":
        description.content_query.filter.return_value.first.return_value = None
    elif unavailable == "archived":
        description.content.archived_at = datetime.now(timezone.utc)
    elif unavailable == "hidden":
        description.visibility.return_value = False
    else:
        description.membership.side_effect = ForbiddenException(detail="Membership revoked")
        expected_exception = ForbiddenException

    with pytest.raises(expected_exception):
        await _download(description)

    description.version_factory.assert_not_called()
    description.storage.list_objects.assert_not_awaited()
    description.storage.download_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_admin_still_needs_actual_membership_and_student_visibility(description):
    description.permissions = Principal(user_id="admin", roles=["_admin"])
    description.membership.side_effect = ForbiddenException(detail="No actual course membership")
    with pytest.raises(ForbiddenException):
        await _download(description)
    description.membership.side_effect = None
    description.visibility.return_value = False
    with pytest.raises(NotFoundException):
        await _download(description)
    description.storage.list_objects.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("release", ["missing", "not-deployed", "pending-version-bump", "failed", "no-version", "unassigned"])
async def test_unreleased_assignment_never_exposes_legacy_or_pending_example_version(description, release):
    # Legacy or staged authoring fields must not become a back door to reference files.
    description.content.example_version_id = RELEASED_VERSION
    description.content.properties = {"example_version_id": RELEASED_VERSION}
    if release == "missing":
        description.deployment_repo.find_latest_for_course_content.return_value = None
    elif release == "not-deployed":
        description.deployment.deployed_at = None
    elif release == "pending-version-bump":
        description.deployment.example_version_id = "new-staged-reference"
        description.deployment.deployment_status = "pending"
    elif release == "failed":
        description.deployment.deployment_status = "failed"
    elif release == "unassigned":
        description.deployment.deployment_status = "unassigned"
    else:
        description.deployment.example_version_id = None

    with pytest.raises(NotFoundException):
        await _download(description)

    description.version_factory.assert_not_called()
    description.storage.list_objects.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["pending", "deploying", "failed"])
async def test_previous_successful_release_remains_available_during_version_bump(description, status):
    description.deployment.deployment_status = status
    description.deployment.example_version_id = "new-staged-reference"
    now = datetime.now(timezone.utc)
    description.history.extend([
        SimpleNamespace(deployment_id="deployment-1", action="deployed", created_at=now - timedelta(days=2),
                        example_version_id="older-released-reference"),
        SimpleNamespace(deployment_id="deployment-1", action="deployed", created_at=now - timedelta(days=1),
                        example_version_id=RELEASED_VERSION),
        SimpleNamespace(deployment_id="deployment-1", action="assigned", created_at=now,
                        example_version_id="new-staged-reference"),
    ])

    archive = await _archive(await _download(description))

    assert archive.read("index.md") == b"# Assignment\nDo this exercise."
    description.version_repo.get_with_relationships.assert_called_once_with(RELEASED_VERSION)


@pytest.mark.asyncio
@pytest.mark.parametrize("history_state", ["missing", "null-version", "only-assigned", "another-deployment"])
async def test_pending_reference_without_successful_matching_release_history_is_unavailable(description, history_state):
    description.deployment.deployment_status = "pending"
    description.deployment.example_version_id = "new-staged-reference"
    if history_state != "missing":
        description.history.append(SimpleNamespace(
            deployment_id="other-deployment" if history_state == "another-deployment" else "deployment-1",
            action="assigned" if history_state == "only-assigned" else "deployed",
            created_at=datetime.now(timezone.utc),
            example_version_id=None if history_state == "null-version" else RELEASED_VERSION,
        ))

    with pytest.raises(NotFoundException):
        await _download(description)

    description.version_factory.assert_not_called()
    description.storage.list_objects.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["version", "example", "repository", "storage-path", "source-url"])
async def test_missing_reference_metadata_returns_not_found_without_reading_storage(description, missing):
    if missing == "version":
        description.version_repo.get_with_relationships.return_value = None
    elif missing == "example":
        description.version.example = None
    elif missing == "repository":
        description.version.example.repository = None
    elif missing == "storage-path":
        description.version.storage_path = ""
    else:
        description.repository.source_url = ""
    with pytest.raises(NotFoundException):
        await _download(description)
    description.storage.list_objects.assert_not_awaited()


@pytest.mark.asyncio
async def test_git_reference_is_not_exposed_by_a_student_download(description):
    description.repository.source_type = "git"
    with pytest.raises(BadRequestException):
        await _download(description)
    description.storage.list_objects.assert_not_awaited()


@pytest.mark.asyncio
async def test_assets_without_any_description_return_not_found(description):
    description.files.clear()
    description.files[f"{PREFIX}/content/images/diagram.png"] = b"image"
    with pytest.raises(NotFoundException):
        await _download(description)


@pytest.mark.asyncio
async def test_duplicate_storage_listing_does_not_duplicate_zip_members(description):
    object_name = f"{PREFIX}/content/index.md"
    description.storage.list_objects.side_effect = None
    description.storage.list_objects.return_value = [
        SimpleNamespace(object_name=object_name), SimpleNamespace(object_name=object_name)
    ]
    archive = await _archive(await _download(description))
    assert archive.namelist() == ["index.md"]
    description.storage.download_file.assert_awaited_once()
