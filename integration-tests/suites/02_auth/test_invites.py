"""Invite-link onboarding — the platform's only registration path.

Covers persona seeding (the golden path's phase 0), who may mint invites, public
metadata + acceptance, and the single-use / revoked guards. Payload-level edge
cases (expiry, email restriction, VAL_001 shapes) live in the 04_contracts suite.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from fixtures.keycloak_auth import authenticate
from fixtures.personas import Persona, PersonaSpec, accept_invite, create_invite

pytestmark = [pytest.mark.auth, pytest.mark.invites]


def _unique(prefix: str) -> str:
    """A fresh email each run — the stack accumulates state (no per-test reset)."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}@integration.test"

_ALL_PERSONAS = ("uma", "orga", "exma", "lena", "tobi", "s_correct", "s_empty", "s_mixed")
_SYSTEM_ROLES = {
    "uma": "_user_manager",
    "orga": "_organization_manager",
    "exma": "_example_manager",
}


def test_all_personas_seeded_and_authenticated(personas: dict[str, Persona]) -> None:
    for name in _ALL_PERSONAS:
        assert name in personas, f"persona {name} not seeded"
        r = personas[name].client.get("/user")
        assert r.status_code == 200, f"{name} whoami failed: {r.status_code} {r.text}"
        assert r.json()["email"] == personas[name].email


def test_key_role_personas_carry_their_system_role(
    personas: dict[str, Persona], admin_client: httpx.Client
) -> None:
    for name, role in _SYSTEM_ROLES.items():
        uid = personas[name].user_id
        r = admin_client.get(f"/user-roles/users/{uid}/roles/{role}")
        assert r.status_code == 200, f"{name} missing {role}: {r.status_code} {r.text}"


def test_user_manager_can_create_invite(uma_client: httpx.Client) -> None:
    r = uma_client.post("/admin/invites", json={"max_uses": 1, "expires_in_days": 7, "roles": []})
    assert r.status_code == 201, r.text


def test_non_manager_cannot_create_invite(lena_client: httpx.Client) -> None:
    # lena has no system role → not an invite manager.
    r = lena_client.post("/admin/invites", json={"max_uses": 1, "expires_in_days": 7, "roles": []})
    assert r.status_code == 403, r.text


def test_public_invite_metadata_is_readable(
    admin_client: httpx.Client, api_base_url: str
) -> None:
    token = create_invite(admin_client, ["_user_manager"], "it metadata")
    r = httpx.get(f"{api_base_url}/invites/{token}", timeout=15)
    assert r.status_code == 200, r.text
    assert "_user_manager" in r.json().get("roles", [])


def test_accept_creates_a_loginable_user(
    admin_client: httpx.Client, api_base_url: str
) -> None:
    token = create_invite(admin_client, [], "it accept")
    spec = PersonaSpec("probe_accept", _unique("probe-accept"), "Pro", "Accept")
    body = accept_invite(api_base_url, token, spec)
    assert body["email"] == spec.email
    creds = authenticate(spec.email, spec.password, api_base=api_base_url)
    r = httpx.get(
        f"{api_base_url}/user", headers={"Authorization": f"Bearer {creds.token}"}, timeout=15
    )
    assert r.status_code == 200 and r.json()["email"] == spec.email


def test_single_use_token_cannot_be_reused(
    admin_client: httpx.Client, api_base_url: str
) -> None:
    token = create_invite(admin_client, [], "it single-use")
    spec = PersonaSpec("probe_reuse", _unique("probe-reuse"), "Pro", "Reuse")
    accept_invite(api_base_url, token, spec)  # first use OK
    r = httpx.post(
        f"{api_base_url}/invites/{token}/accept",
        json={
            "given_name": "Second",
            "family_name": "User",
            "email": _unique("probe-reuse-2"),
            "password": "it-probe-reuse-2-Pass-2099",
        },
        timeout=15,
    )
    assert r.status_code in (400, 403, 409, 410), r.text


def test_revoked_invite_cannot_be_accepted(
    admin_client: httpx.Client, api_base_url: str
) -> None:
    create = admin_client.post(
        "/admin/invites", json={"max_uses": 1, "expires_in_days": 7, "roles": []}
    )
    assert create.status_code == 201, create.text
    invite = create.json()
    revoke = admin_client.delete(f"/admin/invites/{invite['id']}")
    assert revoke.status_code == 204, revoke.text
    r = httpx.post(
        f"{api_base_url}/invites/{invite['token']}/accept",
        json={
            "given_name": "Rev",
            "family_name": "Oked",
            "email": "probe-revoked@integration.test",
            "password": "it-probe-revoked-Pass-2099",
        },
        timeout=15,
    )
    assert r.status_code in (400, 403, 404, 410), r.text
