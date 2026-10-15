"""The idempotent Keycloak setup gives account-console the default scopes it
lacks after a realm import (missing `roles` made the account page fail with 403)."""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location(
    "setup_identity_providers_scopes", REPO / "ops/keycloak/setup_identity_providers.py")
idp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(idp)

BASE = "http://kc"
ADMIN = f"{BASE}/admin/realms/computor"
SCOPES = [{"id": f"id-{n}", "name": n} for n in
          ("web-origins", "openid", "profile", "roles", "email", "role_list", "offline_access")]


def fake_keycloak(monkeypatch, assigned, clients=({"id": "ac"},)):
    puts = []

    def request(method, url, token=None, json_body=None, form_body=None):
        if method == "GET" and url == f"{ADMIN}/clients?clientId=account-console":
            return 200, list(clients)
        if method == "GET" and url == f"{ADMIN}/client-scopes":
            return 200, SCOPES
        if method == "GET" and url == f"{ADMIN}/clients/ac/default-client-scopes":
            return 200, [s for s in SCOPES if s["name"] in assigned]
        if method == "PUT" and url.startswith(f"{ADMIN}/clients/ac/default-client-scopes/"):
            puts.append(url.rsplit("/", 1)[1])
            assigned.add(url.rsplit("/id-", 1)[1])
            return 204, None
        raise AssertionError(f"unexpected {method} {url}")

    monkeypatch.setattr(idp, "_request", request)
    return puts


def test_adds_missing_default_scopes(monkeypatch):
    assigned = set()
    puts = fake_keycloak(monkeypatch, assigned)
    idp.ensure_account_console_scopes(BASE, "computor", "tok")
    assert puts == ["id-web-origins", "id-openid", "id-profile", "id-roles", "id-email"]


def test_is_idempotent_and_leaves_other_scopes(monkeypatch):
    assigned = {"web-origins", "openid", "profile", "roles", "email"}
    puts = fake_keycloak(monkeypatch, assigned)
    idp.ensure_account_console_scopes(BASE, "computor", "tok")
    assert puts == []


def test_missing_client_is_skipped(monkeypatch):
    puts = fake_keycloak(monkeypatch, set(), clients=())
    idp.ensure_account_console_scopes(BASE, "computor", "tok")
    assert puts == []
