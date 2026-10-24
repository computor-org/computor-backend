"""The workspace list reports when each workspace's template version was made.

A workspace's own creation date says nothing about the software inside it,
because starting an outdated workspace rebuilds it on the active version
(computor-org/issues#401). These tests pin the lookup and its cache.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from computor_backend.business_logic.course_workspaces import populate_template_version_dates
from computor_backend.coder.client import CoderClient
from computor_types.coder import CoderWorkspace


def _workspace(name: str, version_id: str | None) -> CoderWorkspace:
    return CoderWorkspace(
        id=f"id-{name}", name=name, owner_id="o1", template_id="t1",
        template_version_id=version_id,
    )


def _client(responses: dict[str, tuple[int, dict]]) -> tuple[CoderClient, list[str]]:
    client = CoderClient(settings=MagicMock())
    paths: list[str] = []

    async def fake_request(method, path, **kwargs):
        paths.append(path)
        status, body = responses[path.rsplit("/", 1)[-1]]
        resp = MagicMock(status_code=status)
        resp.json.return_value = body
        return resp

    client._request = fake_request
    return client, paths


@pytest.mark.asyncio
async def test_each_workspace_gets_its_versions_creation_time():
    client, paths = _client({
        "tv-1": (200, {"created_at": "2026-10-01T08:30:00Z"}),
        "tv-2": (200, {"created_at": "2026-10-20T14:05:00Z"}),
    })
    workspaces = [_workspace("a", "tv-1"), _workspace("b", "tv-2"), _workspace("c", "tv-1")]

    await populate_template_version_dates(client, workspaces)

    assert [w.template_version_created_at.isoformat() for w in workspaces] == [
        "2026-10-01T08:30:00+00:00",
        "2026-10-20T14:05:00+00:00",
        "2026-10-01T08:30:00+00:00",
    ]
    # One request per distinct version, not per workspace.
    assert sorted(paths) == ["/api/v2/templateversions/tv-1", "/api/v2/templateversions/tv-2"]


@pytest.mark.asyncio
async def test_known_versions_are_not_fetched_again():
    client, paths = _client({"tv-1": (200, {"created_at": "2026-10-01T08:30:00Z"})})

    await populate_template_version_dates(client, [_workspace("a", "tv-1")])
    await populate_template_version_dates(client, [_workspace("a", "tv-1")])

    assert paths == ["/api/v2/templateversions/tv-1"]


@pytest.mark.asyncio
async def test_unreadable_version_leaves_the_field_empty():
    client, paths = _client({"tv-x": (404, {})})
    workspaces = [_workspace("a", "tv-x"), _workspace("b", None)]

    await populate_template_version_dates(client, workspaces)
    await populate_template_version_dates(client, workspaces)

    assert [w.template_version_created_at for w in workspaces] == [None, None]
    # A failed lookup is not cached, so it is retried on the next listing.
    assert paths == ["/api/v2/templateversions/tv-x"] * 2


@pytest.mark.asyncio
async def test_a_failing_lookup_does_not_break_the_listing():
    client = MagicMock()
    client.get_template_version_created_at = AsyncMock(side_effect=RuntimeError("coder down"))
    workspace = _workspace("a", "tv-1")

    await populate_template_version_dates(client, [workspace])

    assert workspace.template_version_created_at is None
