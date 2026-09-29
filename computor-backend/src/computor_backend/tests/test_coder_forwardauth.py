"""Unit tests for the Coder ForwardAuth endpoint (verify_coder_access).

Covers the workspace-access authorization gate Traefik calls before forwarding to a
code-server workspace, including the narrow admin exception that lets admins reach the shared
admin/service account's workspace (Coder username "admin", not the u{uuid}
form) but never another user's workspace.
"""

import json

import pytest

from computor_backend.api.auth import verify_coder_access
from computor_backend.coder.naming import encode_coder_username
from computor_backend.permissions.principal import Principal


class _FakeURL:
    def __init__(self, path):
        self.path = path


class _FakeRequest:
    """Minimal stand-in for starlette Request: only .headers, .url and .method are used."""

    def __init__(self, forwarded_uri, path="/", headers=None, method="GET"):
        self.headers = {"X-Forwarded-Uri": forwarded_uri, **(headers or {})}
        self.url = _FakeURL(path)
        self.method = method


# A backend user UUID and the Coder username derived from it.
USER_UUID = "0232de59-e05d-4bc2-898f-b879c06abcde"
USER_OWNER = encode_coder_username(USER_UUID)


def _admin():
    return Principal(user_id="admin-backend-uuid", roles=["_admin"])


def _user(uuid=USER_UUID):
    return Principal(user_id=uuid)  # is_admin stays False


def _body(resp):
    return json.loads(resp.body)


@pytest.mark.asyncio
async def test_admin_can_access_admin_owned_workspace():
    # The case that used to 403 with "Invalid workspace URL format".
    resp = await verify_coder_access(_FakeRequest("/coder/admin/workspace/"), _admin())
    assert resp.status_code == 200
    assert _body(resp)["status"] == "authorized"


@pytest.mark.asyncio
async def test_admin_cannot_access_other_user_workspace():
    # Workspaces run on the app origin: an admin opening a user's workspace
    # would execute that workspace's JS under the admin session.
    resp = await verify_coder_access(_FakeRequest("/coder/%s/workspace/" % USER_OWNER), _admin())
    assert resp.status_code == 403
    assert "administrators do not" in _body(resp)["detail"]


@pytest.mark.asyncio
async def test_admin_can_access_own_workspace():
    admin_uuid = "9f1c2d3e-4a5b-4c6d-8e7f-001122334455"
    admin = Principal(user_id=admin_uuid, roles=["_admin"])
    owner = encode_coder_username(admin_uuid)
    resp = await verify_coder_access(_FakeRequest("/coder/%s/workspace/" % owner), admin)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_service_account_name_follows_env(monkeypatch):
    monkeypatch.setenv("CODER_ADMIN_USERNAME", "svc")
    ok = await verify_coder_access(_FakeRequest("/coder/svc/workspace/"), _admin())
    assert ok.status_code == 200
    denied = await verify_coder_access(_FakeRequest("/coder/admin/workspace/"), _admin())
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_user_can_access_own_workspace():
    resp = await verify_coder_access(_FakeRequest("/coder/%s/workspace/" % USER_OWNER), _user())
    assert resp.status_code == 200
    assert _body(resp)["workspace"] == "workspace"


@pytest.mark.asyncio
async def test_user_can_access_own_workspace_by_encoded_coder_name():
    # The form Coder actually stores: "u" + base32 of the uuid's bytes.
    resp = await verify_coder_access(
        _FakeRequest("/coder/%s/workspace/" % encode_coder_username(USER_UUID)), _user()
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_workspace():
    other = encode_coder_username("ffffffff-ffff-ffff-ffff-ffffffffffff")
    resp = await verify_coder_access(_FakeRequest("/coder/%s/workspace/" % other), _user())
    assert resp.status_code == 403
    assert "not authorized" in _body(resp)["detail"].lower()


@pytest.mark.asyncio
async def test_a_shared_prefix_no_longer_authorizes():
    # Under the old truncating scheme the owner segment was compared with
    # startswith(), so any prefix of the caller's uuid opened their workspace.
    resp = await verify_coder_access(
        _FakeRequest("/coder/u%s/workspace/" % USER_UUID[:20]), _user()
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_undecodable_owner_is_rejected():
    resp = await verify_coder_access(_FakeRequest("/coder/usomebody/workspace/"), _user())
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_workspace():
    # Non-admin hitting /coder/admin/...: owner is not the u{uuid} form -> denied.
    resp = await verify_coder_access(_FakeRequest("/coder/admin/workspace/"), _user())
    assert resp.status_code == 403
    assert "not authorized" in _body(resp)["detail"].lower()


@pytest.mark.asyncio
async def test_malformed_url_is_rejected():
    # No workspace segment -> doesn't match the path shape.
    resp = await verify_coder_access(_FakeRequest("/coder/onlyowner"), _user())
    assert resp.status_code == 403
    assert _body(resp)["detail"] == "Invalid workspace URL format"


# --- No live session (#379): navigations recover via coder-reauth, XHRs 401 ---

_NAV_HEADERS = {"Accept": "text/html,application/xhtml+xml", "X-Forwarded-Method": "GET"}


@pytest.mark.asyncio
async def test_unauthenticated_browser_navigation_redirects_to_reauth():
    resp = await verify_coder_access(
        _FakeRequest("/coder/%s/workspace/" % USER_OWNER, headers=_NAV_HEADERS), None
    )
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "/auth/coder-reauth?" in location
    assert "next=%2Fcoder%2F" in location


@pytest.mark.asyncio
async def test_unauthenticated_xhr_still_gets_401():
    # code-server's own requests advertise no text/html and must keep failing
    # fast — a redirect would only confuse its reconnect logic.
    resp = await verify_coder_access(
        _FakeRequest("/coder/%s/workspace/" % USER_OWNER, headers={"Accept": "*/*"}), None
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_non_get_gets_401():
    resp = await verify_coder_access(
        _FakeRequest(
            "/coder/%s/workspace/" % USER_OWNER,
            headers={"Accept": "text/html", "X-Forwarded-Method": "POST"},
        ),
        None,
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_navigation_to_non_workspace_path_gets_401():
    # Only clean /coder/{owner}/{workspace} paths are worth a reauth round-trip.
    resp = await verify_coder_access(_FakeRequest("/coder/onlyowner", headers=_NAV_HEADERS), None)
    assert resp.status_code == 401


# Distinctive synthetic credential values: asserting the complete value (not a
# header prefix) catches a log line that prints a parsed-out bare token too.
ACCESS = "fa_access_7c1e9d0b5a3f42e8"
REFRESH = "fa_refresh_b84d2f6e19a0c357"
API_TOKEN = "ctp_fa_apitoken_5e0a9c3b71d2"
API_KEY = "fa_apikey_d93b6c20e7f41a58"
_ALL_SECRETS = (ACCESS, REFRESH, API_TOKEN, API_KEY)


def _assert_no_secret_logged(caplog):
    logged = "\n".join(r.getMessage() for r in caplog.records)
    for value in _ALL_SECRETS:
        assert value not in logged


@pytest.mark.asyncio
async def test_credentials_never_reach_the_log(caplog):
    # Every workspace request passes through here; credential headers must not
    # be logged, neither whole nor as the bare token behind "Bearer "/"name=".
    headers = {
        "X-API-Token": API_TOKEN,
        "Cookie": f"ct_access_token={ACCESS}; ct_refresh_token={REFRESH}",
        "Authorization": f"Bearer {ACCESS}",
        "X-API-Key": API_KEY,
    }
    caplog.set_level("DEBUG", logger="computor_backend.api.auth")
    resp = await verify_coder_access(
        _FakeRequest("/coder/%s/workspace/" % USER_OWNER, headers=headers), _user()
    )
    assert resp.status_code == 200
    _assert_no_secret_logged(caplog)


_QUERY = f"?token={ACCESS}&refresh_token={REFRESH}&user_id=x"


@pytest.mark.asyncio
@pytest.mark.parametrize("principal_factory", [_user, _admin])
@pytest.mark.parametrize(
    "uri",
    [
        f"/coder/{USER_OWNER}/workspace{_QUERY}",  # no trailing slash
        f"/coder/{USER_OWNER}/workspace/{_QUERY}",  # trailing slash
        f"/coder/{USER_OWNER}/workspace/proxy/8080/{_QUERY}#frag",
    ],
)
async def test_query_credentials_in_workspace_url_never_logged(caplog, uri, principal_factory):
    # The SSO callback redirect puts token/refresh_token into the workspace URL
    # query; ForwardAuth sees it in X-Forwarded-Uri on every request.
    caplog.set_level("DEBUG", logger="computor_backend.api.auth")
    resp = await verify_coder_access(_FakeRequest(uri), principal_factory())
    # Admins may no longer open other users' workspaces (403); the owner may.
    # Either way no credential from the query may reach the log.
    if principal_factory is _user:
        assert resp.status_code == 200
        # The query is not part of the workspace identity.
        assert _body(resp)["workspace"] == "workspace"
    else:
        assert resp.status_code == 403
    _assert_no_secret_logged(caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "uri",
    [
        f"/invalid{_QUERY}",
        f"/coder/{USER_OWNER}{_QUERY}",  # owner only, query right after it
        f"/coder/{USER_OWNER}/{_QUERY}",
        f"/coder/{USER_OWNER}/work%3Fspace{_QUERY}",  # encoded "?" in the segment
    ],
)
async def test_rejected_workspace_url_is_not_echoed_to_the_log(caplog, uri):
    caplog.set_level("DEBUG", logger="computor_backend.api.auth")
    resp = await verify_coder_access(_FakeRequest(uri), _user())
    assert resp.status_code == 403
    _assert_no_secret_logged(caplog)


@pytest.mark.asyncio
async def test_foreign_workspace_with_query_credentials_never_logged(caplog):
    caplog.set_level("DEBUG", logger="computor_backend.api.auth")
    other = encode_coder_username("11111111-2222-3333-4444-555555555555")
    resp = await verify_coder_access(_FakeRequest(f"/coder/{other}/ws/{_QUERY}"), _user())
    assert resp.status_code == 403
    _assert_no_secret_logged(caplog)
