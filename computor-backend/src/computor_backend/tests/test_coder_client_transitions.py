"""Rich-parameter handling on workspace builds.

Coder resets any rich parameter a build omits back to the template default, so
a build that sends an explicit parameter list has to carry forward everything
it still wants. Two classes of value matter:

* the immutable set (``CARRIED_BUILD_PARAMS``) — home mode, root/internet
  policy, the course marker, the app credential;
* ``computor_auth_token``, which is *mutable* and therefore not in that set,
  but is reset to the template's ``""`` default just the same — which
  de-authenticates the VS Code extension inside the workspace.

These tests pin both, plus the override precedence the rotation push relies on,
and the auto-stop TTL convergence the start path performs (see that section's
comment for why Coder's creation-time TTL snapshot makes it necessary).
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


def _client(
    build_params=None,
    active_version_id="tv-1",
    current_ttl_ms=3_600_000,
    ttl_put_fails=False,
):
    """A CoderClient with only the HTTP layer faked out.

    The previous build sits on ``tv-1``; ``active_version_id`` is what the
    template currently promotes — pass ``"tv-2"`` to model a workspace a
    template push has left behind. ``current_ttl_ms`` is the workspace's
    stored auto-stop TTL (``None`` models one created before the templates
    carried a TTL — the never-auto-stops case).
    """
    client = CoderClient.__new__(CoderClient)
    client.settings = MagicMock(workspace_timeout=30, workspace_ttl_ms=3_600_000)
    client.get_build_params = AsyncMock(
        return_value=dict(PREVIOUS_BUILD if build_params is None else build_params)
    )

    posted = {}

    async def fake_request(method, path, **kwargs):
        resp = MagicMock()
        if method == "GET":
            resp.status_code = 200
            resp.json.return_value = {
                "latest_build": {"id": "build-1", "template_version_id": "tv-1"},
                "template_active_version_id": active_version_id,
                "ttl_ms": current_ttl_ms,
            }
        elif method == "PUT":
            if ttl_put_fails:
                raise RuntimeError("coder unreachable")
            posted.setdefault("ttl_puts", []).append(
                {"path": path, "json": kwargs.get("json")}
            )
            resp.status_code = 200
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


# --- active-version adoption on start ----------------------------------------


@pytest.mark.asyncio
async def test_start_builds_on_the_active_version_when_outdated():
    # The rollout regression: every start re-pinned the previous build's
    # version, so a pushed template never reached an existing workspace no
    # matter how often it was restarted.
    client = _client(active_version_id="tv-2")
    await client._workspace_transition("ws-1", "start")
    assert client._posted["body"]["template_version_id"] == "tv-2"


@pytest.mark.asyncio
async def test_version_change_start_carries_the_parameters():
    # A version-change build re-resolves parameters against the new version,
    # so even a plain start must send the explicit list once the version
    # moves — otherwise the auth token resets to "" and logs the extension out.
    client = _client(active_version_id="tv-2")
    await client._workspace_transition("ws-1", "start")
    sent = _sent(client)
    assert sent["computor_auth_token"] == "ctp_previous_token"
    assert sent["home_mode"] == "scratch"
    assert sent["workspace_app_secret"] == "old-secret"


@pytest.mark.asyncio
async def test_stop_keeps_the_version_it_was_built_with():
    # Teardown must run the terraform that created the resources.
    client = _client(active_version_id="tv-2")
    await client._workspace_transition("ws-1", "stop")
    assert client._posted["body"]["template_version_id"] == "tv-1"
    assert "rich_parameter_values" not in client._posted["body"]


@pytest.mark.asyncio
async def test_current_workspace_start_stays_on_the_cheap_path():
    # No version change, no policy, no overrides: Coder carries everything
    # forward itself, exactly as before.
    client = _client(active_version_id="tv-1")
    await client._workspace_transition("ws-1", "start")
    assert client._posted["body"]["template_version_id"] == "tv-1"
    assert "rich_parameter_values" not in client._posted["body"]
    client.get_build_params.assert_not_awaited()


# --- auto-stop TTL convergence on start ---------------------------------------
#
# Coder snapshots the template's default_ttl_ms into the workspace at creation
# and never consults the template again: a workspace created while its template
# carried no TTL has a null ttl and never auto-stops (the immortal-MATLAB-
# workspace bug), and a config change reaches no existing workspace. The start
# path converges every workspace on the configured TTL before the build
# computes its deadline.


@pytest.mark.asyncio
async def test_start_backfills_a_missing_ttl_before_the_build():
    client = _client(current_ttl_ms=None)
    await client._workspace_transition("ws-1", "start")
    assert client._posted["ttl_puts"] == [
        {"path": "/api/v2/workspaces/ws-1/ttl", "json": {"ttl_ms": 3_600_000}}
    ]
    assert client._posted["body"]["transition"] == "start"


@pytest.mark.asyncio
async def test_start_converges_a_stale_ttl():
    # Lowering the configured TTL must reach existing workspaces too, not just
    # newly created ones — their snapshot is otherwise frozen forever.
    client = _client(current_ttl_ms=14_400_000)
    await client._workspace_transition("ws-1", "start")
    assert client._posted["ttl_puts"][0]["json"] == {"ttl_ms": 3_600_000}


@pytest.mark.asyncio
async def test_start_leaves_a_matching_ttl_alone():
    client = _client()
    await client._workspace_transition("ws-1", "start")
    assert "ttl_puts" not in client._posted


@pytest.mark.asyncio
async def test_stop_never_touches_the_ttl():
    # The deadline is computed on start, so fixing scheduling on the stop path
    # buys nothing — and must never stand between the user and a teardown.
    client = _client(current_ttl_ms=None)
    await client._workspace_transition("ws-1", "stop")
    assert "ttl_puts" not in client._posted


@pytest.mark.asyncio
async def test_ttl_failure_does_not_block_the_start():
    # Best-effort: a Coder hiccup on the scheduling call must not cost the
    # user their workspace start.
    client = _client(current_ttl_ms=None, ttl_put_fails=True)
    assert await client._workspace_transition("ws-1", "start") is True
    assert client._posted["body"]["transition"] == "start"


@pytest.mark.asyncio
async def test_create_workspace_states_the_ttl_itself():
    # Relying on the template default reintroduces the creation-time snapshot
    # race (workspace created before the template's TTL was pushed).
    from computor_backend.coder.schemas import CoderWorkspaceCreate

    client = _client()
    client.get_template_id = AsyncMock(return_value="tpl-1")

    async def fake_create(method, path, **kwargs):
        client._posted["body"] = kwargs.get("json")
        resp = MagicMock()
        resp.status_code = 201
        resp.json.return_value = {
            "id": "ws-1", "name": "w1", "owner_id": "u1", "template_id": "tpl-1",
        }
        return resp

    client._request = AsyncMock(side_effect=fake_create)
    await client.create_workspace(
        "u1", CoderWorkspaceCreate(name="w1", template="vscode-workspace")
    )
    assert client._posted["body"]["ttl_ms"] == 3_600_000


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
