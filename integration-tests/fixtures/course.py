"""Seed the org → course-family → course hierarchy with a Forgejo git binding.

Golden-path phase 1 (03-personas §Phase 1): the org-manager (`orga`) builds the
hierarchy, binds the course to the managed Forgejo (which materializes the
student-template repo and locks the binding), and seats the lecturer + tutor —
seating a `_tutor` needs authority above a plain lecturer (the assignment
ceiling), which the org-manager has.

All fixtures are session-scoped and idempotent (find-or-create), matching the
no-reset run model.
"""

from __future__ import annotations

import httpx
import pytest

ORG_PATH = "it_org"
ORG_TITLE = "IT Org"
COURSE_FAMILY_PATH = "it_family"
COURSE_FAMILY_TITLE = "IT Family"
COURSE_PATH = "it_course_py"
COURSE_TITLE = "IT Python Course"


def _find_by_path(client: httpx.Client, resource: str, path: str) -> dict | None:
    r = client.get(f"/{resource}")
    r.raise_for_status()
    return next((x for x in r.json() if x.get("path") == path), None)


@pytest.fixture(scope="session")
def managed_git_server_id(orga_client: httpx.Client) -> str:
    r = orga_client.get("/git-servers")
    r.raise_for_status()
    for server in r.json():
        if server.get("type") == "forgejo" and server.get("managed"):
            return server["id"]
    raise AssertionError("no managed Forgejo git server registered")


@pytest.fixture(scope="session")
def target_organization(orga_client: httpx.Client) -> dict:
    existing = _find_by_path(orga_client, "organizations", ORG_PATH)
    if existing is not None:
        return existing
    r = orga_client.post(
        "/organizations",
        json={"path": ORG_PATH, "organization_type": "organization", "title": ORG_TITLE},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


@pytest.fixture(scope="session")
def target_course_family(orga_client: httpx.Client, target_organization: dict) -> dict:
    existing = _find_by_path(orga_client, "course-families", COURSE_FAMILY_PATH)
    if existing is not None:
        return existing
    r = orga_client.post(
        "/course-families",
        json={
            "path": COURSE_FAMILY_PATH,
            "organization_id": target_organization["id"],
            "title": COURSE_FAMILY_TITLE,
        },
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


@pytest.fixture(scope="session")
def target_course(orga_client: httpx.Client, target_course_family: dict) -> dict:
    existing = _find_by_path(orga_client, "courses", COURSE_PATH)
    if existing is not None:
        return existing
    r = orga_client.post(
        "/courses",
        json={
            "path": COURSE_PATH,
            "course_family_id": target_course_family["id"],
            "title": COURSE_TITLE,
        },
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


@pytest.fixture(scope="session")
def target_course_git(
    orga_client: httpx.Client, target_course: dict, managed_git_server_id: str
) -> dict:
    """Bind the course to the managed Forgejo (idempotent).

    The first PUT materializes the student-template repo and locks the binding,
    so on re-run we detect the existing binding and skip the PUT.
    """
    course_id = target_course["id"]
    existing = orga_client.get(f"/courses/{course_id}/git")
    if existing.status_code == 200 and existing.json().get("git_server_id"):
        return existing.json()
    r = orga_client.put(
        f"/courses/{course_id}/git",
        json={
            "delivery": "git",
            "git_server_id": managed_git_server_id,
            "student_repo_modes": ["managed"],
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def _ensure_course_member(
    orga_client: httpx.Client,
    course_id: str,
    user_id: str,
    course_role_id: str,
    course_group_id: str | None = None,
) -> dict:
    listing = orga_client.get(
        "/course-members", params={"course_id": course_id, "user_id": user_id}
    )
    listing.raise_for_status()
    for m in listing.json():
        if m.get("user_id") == user_id and m.get("course_id") == course_id:
            return m
    body: dict = {"user_id": user_id, "course_id": course_id, "course_role_id": course_role_id}
    if course_group_id is not None:
        body["course_group_id"] = course_group_id
    r = orga_client.post("/course-members", json=body)
    assert r.status_code in (200, 201), r.text
    return r.json()


@pytest.fixture(scope="session")
def seated_staff(orga_client: httpx.Client, target_course: dict, personas: dict) -> dict:
    """Seat lena as _lecturer and tobi as _tutor (org-manager is uncapped)."""
    course_id = target_course["id"]
    return {
        "lecturer": _ensure_course_member(
            orga_client, course_id, personas["lena"].user_id, "_lecturer"
        ),
        "tutor": _ensure_course_member(
            orga_client, course_id, personas["tobi"].user_id, "_tutor"
        ),
    }
