"""Seed the canonical test personas via the real invite-onboarding flow.

This is the golden path's phase 0 ([testing-strategy] 03-personas): the admin
mints role-carrying invites for the key-role personas, they accept and log in,
then the user-manager invites the course actors. Every persona is created the
way a real user is — no direct DB writes — and authenticates via the SSO dance.

System-role personas (created by admin):
    uma   → _user_manager
    orga  → _organization_manager
    exma  → _example_manager

Course-actor personas (created by uma; their COURSE roles are assigned later,
during course setup — the role-assignment ceiling means orga seats lecturer/tutor
and lena enrols students):
    lena, tobi, s_correct, s_empty, s_mixed   (no system roles)

Idempotent: a persona that already exists (re-run against a live stack) is just
logged in again. Fixed emails/passwords keep re-runs stable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional

import httpx
import pytest

from fixtures.api import DEFAULT_TIMEOUT
from fixtures.keycloak_auth import Credentials, authenticate


@dataclass(frozen=True)
class PersonaSpec:
    name: str
    email: str
    given_name: str
    family_name: str
    system_roles: tuple[str, ...] = ()
    invited_by: str = "admin"  # persona key of the inviter

    @property
    def password(self) -> str:
        return f"it-{self.name}-Pass-2099"


@dataclass
class Persona:
    spec: PersonaSpec
    creds: Credentials
    client: httpx.Client

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def email(self) -> str:
        return self.spec.email

    @property
    def user_id(self) -> Optional[str]:
        return self.creds.user_id

    @property
    def token(self) -> str:
        return self.creds.token


# Order matters: key-role personas first (invited by admin), then course actors
# (invited by uma, which must exist and be logged in by then).
PERSONA_SPECS: tuple[PersonaSpec, ...] = (
    PersonaSpec("uma", "uma@integration.test", "Ursula", "Manager", ("_user_manager",)),
    PersonaSpec("orga", "orga@integration.test", "Otto", "Organizer", ("_organization_manager",)),
    PersonaSpec("exma", "exma@integration.test", "Ewa", "Examples", ("_example_manager",)),
    PersonaSpec("lena", "lena@integration.test", "Lena", "Lecturer", (), "uma"),
    PersonaSpec("tobi", "tobi@integration.test", "Tobias", "Tutor", (), "uma"),
    PersonaSpec("s_correct", "s-correct@integration.test", "Cora", "Correct", (), "uma"),
    PersonaSpec("s_empty", "s-empty@integration.test", "Emil", "Empty", (), "uma"),
    PersonaSpec("s_mixed", "s-mixed@integration.test", "Mila", "Mixed", (), "uma"),
)


def _find_user_by_email(admin_client: httpx.Client, email: str) -> Optional[dict]:
    r = admin_client.get("/users", params={"search": email})
    r.raise_for_status()
    for item in r.json():
        if (item.get("email") or "").lower() == email.lower():
            return item
    return None


def create_invite(inviter: httpx.Client, roles: list[str], note: str) -> str:
    """Mint a single-use invite carrying the given system roles; return its token."""
    r = inviter.post(
        "/admin/invites",
        json={"max_uses": 1, "expires_in_days": 7, "roles": roles, "note": note},
    )
    assert r.status_code == 201, f"create invite failed: {r.status_code} {r.text}"
    return r.json()["token"]


def accept_invite(api_base_url: str, token: str, spec: PersonaSpec) -> dict:
    """Public invite acceptance — creates the Keycloak login + computor User."""
    r = httpx.post(
        f"{api_base_url}/invites/{token}/accept",
        json={
            "given_name": spec.given_name,
            "family_name": spec.family_name,
            "email": spec.email,
            "password": spec.password,
        },
        timeout=DEFAULT_TIMEOUT,
    )
    assert r.status_code == 201, f"accept invite failed for {spec.email}: {r.status_code} {r.text}"
    return r.json()


def _ensure_persona(
    spec: PersonaSpec,
    *,
    admin_client: httpx.Client,
    inviter: httpx.Client,
    api_base_url: str,
) -> Persona:
    if _find_user_by_email(admin_client, spec.email) is None:
        token = create_invite(inviter, list(spec.system_roles), note=f"it persona {spec.name}")
        accept_invite(api_base_url, token, spec)
    creds = authenticate(spec.email, spec.password, api_base=api_base_url)
    client = httpx.Client(
        base_url=api_base_url,
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=DEFAULT_TIMEOUT,
    )
    return Persona(spec=spec, creds=creds, client=client)


@pytest.fixture(scope="session")
def personas(admin_client: httpx.Client, api_base_url: str) -> Iterator[dict[str, Persona]]:
    """The full persona registry, seeded via invites and logged in once each."""
    registry: dict[str, Persona] = {}
    for spec in PERSONA_SPECS:
        inviter = admin_client if spec.invited_by == "admin" else registry[spec.invited_by].client
        registry[spec.name] = _ensure_persona(
            spec, admin_client=admin_client, inviter=inviter, api_base_url=api_base_url
        )
    yield registry
    for persona in registry.values():
        persona.client.close()
