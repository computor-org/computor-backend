"""ensure_client_redirect_uris reconciles the client's rootUrl/baseUrl (issues#478).

Keycloak's "Back to application" link points at the client baseUrl; the realm
import ships http://localhost:8000, so a deployment must overwrite it.
"""

import asyncio

import computor_backend.auth.keycloak_admin as kc_mod

URIS = ["https://computor.at/api/auth/keycloak/callback", "https://computor.at/"]
ORIGINS = ["https://computor.at"]


def _reconcile(monkeypatch, kc_client, **kwargs):
    puts = []

    class _Response:
        status_code = 200

        def __init__(self, body=None):
            self._body = body

        def json(self):
            return self._body

        def raise_for_status(self):
            pass

    class _Client:
        def __init__(self, *args, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, params=None, headers=None):
            return _Response([dict(kc_client)])

        async def put(self, url, json=None, headers=None):
            puts.append(json)
            return _Response()

    async def _token(self):
        return "tok"

    monkeypatch.setattr(kc_mod.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(kc_mod.KeycloakAdminClient, "_get_admin_token", _token)
    asyncio.run(kc_mod.KeycloakAdminClient().ensure_client_redirect_uris(URIS, ORIGINS, **kwargs))
    return puts


def _client(**over):
    return {
        "id": "internal",
        "clientId": "computor-backend",
        "redirectUris": list(URIS),
        "webOrigins": list(ORIGINS),
        "rootUrl": "http://localhost:8000",
        "baseUrl": "http://localhost:8000",
        **over,
    }


def test_stale_base_url_is_overwritten(monkeypatch):
    puts = _reconcile(monkeypatch, _client(), base_url="https://computor.at/")
    assert len(puts) == 1
    assert puts[0]["rootUrl"] == "https://computor.at/"
    assert puts[0]["baseUrl"] == "https://computor.at/"


def test_current_base_url_writes_nothing(monkeypatch):
    current = _client(rootUrl="https://computor.at/", baseUrl="https://computor.at/")
    assert _reconcile(monkeypatch, current, base_url="https://computor.at/") == []


def test_without_base_url_leaves_urls_alone(monkeypatch):
    puts = _reconcile(monkeypatch, _client(redirectUris=[]))
    assert len(puts) == 1
    assert puts[0]["baseUrl"] == "http://localhost:8000"
