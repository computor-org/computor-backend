"""Rich-parameter handling on workspace builds.

Coder resets any rich parameter a build omits back to the template default, so
a build that sends an explicit parameter list has to carry forward everything
it still wants. Two classes of value matter:

* the immutable set (``CARRIED_BUILD_PARAMS``) — home mode, root/internet
  policy, the course marker, the app credential;
* ``computor_auth_token``, which is *mutable* and therefore not in that set,
  but is reset to the template's ``""`` default just the same — which
  de-authenticates the VS Code extension inside the workspace.

These tests pin both, plus the override precedence the rotation push relies on.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from computor_backend.coder.client import CoderClient


PREVIOUS_BUILD = {
    "home_mode": "scratch",
    "allow_root": "false",
    "allow_internet": "false",
    "course_id": "course-1",
    "workspace_app_secret": "old-secret",
    "workspace_app_hash": "$argon2id$old",
    "computor_auth_token": "ctp_previous_token",
}


def _client(build_params=None):
    """A CoderClient with only the HTTP layer faked out."""
    client = CoderClient.__new__(CoderClient)
    client.settings = MagicMock(workspace_timeout=30)
    client.get_build_params = AsyncMock(
        return_value=dict(PREVIOUS_BUILD if build_params is None else build_params)
    )

    posted = {}

    async def fake_request(method, path, **kwargs):
        resp = MagicMock()
        if method == "GET":
            resp.status_code = 200
            resp.json.return_value = {
                "latest_build": {"id": "build-1", "template_version_id": "tv-1"}
            }
        else:
            posted["body"] = kwargs.get("json")
            resp.status_code = 200
        return resp

    client._request = AsyncMock(side_effect=fake_request)
    client._posted = posted
    return client


def _sent(client) -> dict:
    """Rich parameters of the build that was posted, as a name -> value dict."""
    values = client._posted["body"].get("rich_parameter_values")
    if values is None:
        return {}
    names = [v["name"] for v in values]
    assert len(names) == len(set(names)), f"duplicate parameter names: {names}"
    return {v["name"]: v["value"] for v in values}


@pytest.mark.asyncio
async def test_plain_transition_sends_no_parameters_at_all():
    # An ordinary stop/start must let Coder carry everything forward itself;
    # sending a list here would be the reset bug in a different disguise.
    client = _client()
    await client._workspace_transition("ws-1", "stop")
    assert "rich_parameter_values" not in client._posted["body"]
    client.get_build_params.assert_not_awaited()


@pytest.mark.asyncio
async def test_policy_build_preserves_the_auth_token():
    # The regression: the extension's token was reset to "" on every
    # policy-carrying start, silently logging the workspace out of the API.
    client = _client()
    await client._workspace_transition(
        "ws-1", "start", policy={"allow_root": True, "allow_internet": True}
    )
    sent = _sent(client)
    assert sent["computor_auth_token"] == "ctp_previous_token"


@pytest.mark.asyncio
async def test_policy_build_carries_the_immutable_set_and_applies_the_policy():
    client = _client()
    await client._workspace_transition(
        "ws-1", "start", policy={"allow_root": True, "allow_internet": False}
    )
    sent = _sent(client)
    assert sent["home_mode"] == "scratch"
    assert sent["course_id"] == "course-1"
    assert sent["workspace_app_secret"] == "old-secret"
    assert sent["allow_root"] == "true"      # policy wins over the carried value
    assert sent["allow_internet"] == "false"


@pytest.mark.asyncio
async def test_param_overrides_replace_carried_values():
    client = _client()
    await client.rebuild_with_params(
        "ws-1",
        {"workspace_app_secret": "new-secret", "workspace_app_hash": "$argon2id$new"},
    )
    sent = _sent(client)
    assert sent["workspace_app_secret"] == "new-secret"
    assert sent["workspace_app_hash"] == "$argon2id$new"
    # Everything else still rides along, token included.
    assert sent["home_mode"] == "scratch"
    assert sent["computor_auth_token"] == "ctp_previous_token"


@pytest.mark.asyncio
async def test_overrides_win_over_policy_on_the_same_key():
    client = _client()
    await client._workspace_transition(
        "ws-1", "start",
        policy={"allow_root": True},
        param_overrides={"allow_root": "false"},
    )
    assert _sent(client)["allow_root"] == "false"


@pytest.mark.asyncio
async def test_unreadable_previous_build_still_applies_the_override():
    # get_build_params returns {} when Coder cannot be read; the override must
    # still land rather than the build being sent with nothing at all.
    client = _client(build_params={})
    await client.rebuild_with_params("ws-1", {"workspace_app_secret": "new-secret"})
    assert _sent(client) == {"workspace_app_secret": "new-secret"}


@pytest.mark.asyncio
async def test_token_update_merges_extra_params_without_duplicates():
    client = _client()
    client._carry_build_params = AsyncMock(
        return_value=[{"name": n, "value": v} for n, v in PREVIOUS_BUILD.items()
                      if n != "computor_auth_token"]
    )
    await client._update_workspace_token(
        "ws-1", "ctp_new_token",
        extra_params={"workspace_app_secret": "new-secret"},
    )
    sent = _sent(client)  # also asserts there are no duplicate names
    assert sent["computor_auth_token"] == "ctp_new_token"
    assert sent["workspace_app_secret"] == "new-secret"
    assert sent["home_mode"] == "scratch"


# --- fleet rollout ------------------------------------------------------------


def _rollout_client():
    client = _client()
    client._carry_build_params = AsyncMock(
        return_value=[{"name": n, "value": v} for n, v in PREVIOUS_BUILD.items()
                      if n != "computor_auth_token"]
    )
    client._get_build_param = AsyncMock(return_value="ctp_previous_token")
    return client


@pytest.mark.asyncio
async def test_rollout_replaces_the_credential_when_the_caller_supplies_one():
    client = _rollout_client()
    await client.update_workspace_to_version(
        "ws-1", "tv-2", credentials=("fresh-secret", "$argon2id$fresh")
    )
    sent = _sent(client)
    assert sent["workspace_app_secret"] == "fresh-secret"
    assert sent["workspace_app_hash"] == "$argon2id$fresh"
    assert sent["computor_auth_token"] == "ctp_previous_token"
    assert sent["home_mode"] == "scratch"


@pytest.mark.asyncio
async def test_rollout_carries_the_previous_credential_without_one():
    # Coder's own admin account or a deleted user: nothing to resolve, so the
    # workspace keeps the credential it has rather than getting one derived
    # from a string that is not the user id.
    client = _rollout_client()
    await client.update_workspace_to_version("ws-1", "tv-2")
    sent = _sent(client)
    assert sent["workspace_app_secret"] == "old-secret"


@pytest.mark.asyncio
async def test_rollout_never_derives_a_credential_itself(monkeypatch):
    """The client has no database session, so it cannot know the key version.

    It used to derive from the Coder owner_name, which is not the user id — a
    truncated one under the old naming scheme — producing a secret nothing else
    could reproduce.
    """
    monkeypatch.setenv("TOKEN_SECRET", "x" * 32)
    client = _rollout_client()
    client.get_build_params = AsyncMock(return_value={})
    client._carry_build_params = AsyncMock(return_value=[])
    client._get_build_param = AsyncMock(return_value=None)

    await client.update_workspace_to_version("ws-1", "tv-2")

    assert "workspace_app_secret" not in _sent(client)
