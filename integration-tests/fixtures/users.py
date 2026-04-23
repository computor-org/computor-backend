"""Seed the canonical role-bearing test users and their course memberships.

Roles (course-scoped, handoff fictional names):
    bob-owner         → _owner
    carol-maintainer  → _maintainer
    dave-lecturer     → _lecturer
    erin-tutor        → _tutor
    frank-student1    → _student

The admin user is created at server startup from `API_ADMIN_USER`; we only
seed the other five here. Everything is idempotent: a repeat run finds
existing users and memberships and returns them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import httpx
import pytest


# Strong-enough-to-satisfy-admin-set-password (min 12 chars). Fine for a
# throwaway test stack; nothing sensitive is behind these users.
ROLE_PASSWORD = "IntegrationTest!2099"


@dataclass(frozen=True)
class SeedUser:
    username: str
    given_name: str
    family_name: str
    course_role: str  # e.g. "_owner", "_student"


SEED_USERS: tuple[SeedUser, ...] = (
    SeedUser("bob-owner", "Bob", "Owner", "_owner"),
    SeedUser("carol-maintainer", "Carol", "Maintainer", "_maintainer"),
    SeedUser("dave-lecturer", "Dave", "Lecturer", "_lecturer"),
    SeedUser("erin-tutor", "Erin", "Tutor", "_tutor"),
    SeedUser("frank-student1", "Frank", "Student", "_student"),
)


def _find_user(client: httpx.Client, username: str) -> dict | None:
    r = client.get("/users", params={"username": username})
    r.raise_for_status()
    for item in r.json():
        if item.get("username") == username:
            return item
    return None


def _ensure_user(client: httpx.Client, spec: SeedUser) -> dict:
    existing = _find_user(client, spec.username)
    if existing is not None:
        return existing
    r = client.post(
        "/users",
        json={
            "username": spec.username,
            "given_name": spec.given_name,
            "family_name": spec.family_name,
            "email": f"{spec.username}@example.test",
        },
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


def _ensure_password(client: httpx.Client, username: str, password: str) -> None:
    r = client.post(
        "/password/admin/set",
        json={
            "username": username,
            "new_password": password,
            "confirm_password": password,
        },
    )
    # 200 on success; 409/400 if already set identically — re-setting is cheap
    # enough that we don't special-case and just assert success.
    assert r.status_code in (200, 204), r.text


def _ensure_course_member(
    client: httpx.Client,
    user_id: str,
    course_id: str,
    course_role_id: str,
    course_group_id: str | None = None,
) -> dict:
    listing = client.get(
        "/course-members", params={"user_id": user_id, "course_id": course_id}
    )
    listing.raise_for_status()
    for item in listing.json():
        if item.get("user_id") == user_id and item.get("course_id") == course_id:
            return item

    body: dict = {
        "user_id": user_id,
        "course_id": course_id,
        "course_role_id": course_role_id,
    }
    # DB CHECK: students require course_group_id. Non-students are fine
    # either way.
    if course_group_id is not None:
        body["course_group_id"] = course_group_id
    r = client.post("/course-members", json=body)
    assert r.status_code in (200, 201), r.text
    return r.json()


@pytest.fixture(scope="session")
def role_password() -> str:
    return ROLE_PASSWORD


@pytest.fixture(scope="session")
def seed_role_users(
    admin_client: httpx.Client,
    target_course: dict,
    target_course_group: dict,
    role_password: str,
) -> dict[str, dict]:
    """Create the five role-bearing users, set their passwords, and assign
    them into the target course with the appropriate course role.

    Returns a dict keyed by course role (e.g. ``"_owner"``) whose values are
    the full user dicts returned by the API. Callers use this both to look
    up user IDs and to drive per-role login in the client fixtures.
    """
    out: dict[str, dict] = {}
    for spec in SEED_USERS:
        user = _ensure_user(admin_client, spec)
        _ensure_password(admin_client, spec.username, role_password)
        _ensure_course_member(
            admin_client,
            user_id=user["id"],
            course_id=target_course["id"],
            course_role_id=spec.course_role,
            course_group_id=(
                target_course_group["id"] if spec.course_role == "_student" else None
            ),
        )
        # Stash the spec too so the client fixtures can look up usernames
        # without re-importing SEED_USERS.
        out[spec.course_role] = {**user, "password": role_password, "spec": spec}
    return out
