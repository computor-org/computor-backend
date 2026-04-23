"""Seed the canonical org → course-family → course hierarchy.

Uses the fictional identities listed in the handoff (acme-university /
intro-to-programming / py-fall-2099). Idempotent so the suite can be re-run
against a dirty stack without a full volume wipe.

Organization and CourseFamily are created via the admin API. Course is
inserted directly via SQL because `CourseCreate` doesn't expose
`organization_id` but the underlying table requires it (see fixtures/db.py
for the note).
"""

from __future__ import annotations

from typing import Iterator

import httpx
import psycopg
import pytest

ORG_PATH = "acme-university"
ORG_TITLE = "ACME University"
COURSE_FAMILY_PATH = "intro-to-programming"
COURSE_FAMILY_TITLE = "Intro to Programming"
COURSE_PATH = "py-fall-2099"
COURSE_TITLE = "Python Fall 2099"
COURSE_GROUP_TITLE = "Default Group"


def _find_by_path(client: httpx.Client, resource: str, path: str) -> dict | None:
    r = client.get(f"/{resource}")
    r.raise_for_status()
    for item in r.json():
        if item.get("path") == path:
            return item
    return None


@pytest.fixture(scope="session")
def target_organization(admin_client: httpx.Client) -> dict:
    existing = _find_by_path(admin_client, "organizations", ORG_PATH)
    if existing is not None:
        return existing
    r = admin_client.post(
        "/organizations",
        json={
            "path": ORG_PATH,
            "organization_type": "organization",
            "title": ORG_TITLE,
        },
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


@pytest.fixture(scope="session")
def target_course_family(
    admin_client: httpx.Client, target_organization: dict
) -> dict:
    existing = _find_by_path(admin_client, "course-families", COURSE_FAMILY_PATH)
    if existing is not None:
        return existing
    r = admin_client.post(
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
def target_course(
    db_conn: psycopg.Connection,
    admin_client: httpx.Client,
    target_course_family: dict,
    target_organization: dict,
) -> dict:
    # Try the API first in case a future backend fix lands and this fallback
    # becomes unnecessary.
    existing = _find_by_path(admin_client, "courses", COURSE_PATH)
    if existing is not None:
        return existing

    api_attempt = admin_client.post(
        "/courses",
        json={
            "path": COURSE_PATH,
            "course_family_id": target_course_family["id"],
            "title": COURSE_TITLE,
        },
    )
    if api_attempt.status_code in (200, 201):
        return api_attempt.json()

    # DB fallback: organization_id NOT NULL, DTO doesn't expose it.
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO course (path, course_family_id, organization_id, title)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                COURSE_PATH,
                target_course_family["id"],
                target_organization["id"],
                COURSE_TITLE,
            ),
        )
        row = cur.fetchone()
        assert row is not None
        course_id = row[0]

    # Re-fetch through the API so the returned dict matches the CourseGet shape.
    r = admin_client.get(f"/courses/{course_id}")
    r.raise_for_status()
    return r.json()


@pytest.fixture(scope="session")
def target_course_group(
    admin_client: httpx.Client, target_course: dict
) -> dict:
    """Default course group for student memberships.

    The ``course_member`` table has a CHECK constraint requiring
    ``course_group_id`` to be non-null when ``course_role_id = '_student'``,
    so students need a group to land in.
    """
    existing = admin_client.get(
        "/course-groups", params={"course_id": target_course["id"]}
    )
    existing.raise_for_status()
    for item in existing.json():
        if item.get("course_id") == target_course["id"] and item.get("title") == COURSE_GROUP_TITLE:
            return item

    r = admin_client.post(
        "/course-groups",
        json={"course_id": target_course["id"], "title": COURSE_GROUP_TITLE},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()
