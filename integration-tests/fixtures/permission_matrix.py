"""RBAC permission matrix: one row per ``(method, path)`` with per-role
expected HTTP status codes.

Lives under ``fixtures/`` so the test files in ``suites/03_permissions/``
can import it cleanly (the suite directories are named with a leading
digit, which is not a valid Python package identifier, so normal relative
imports within ``suites/03_permissions/`` don't work).

Column keys (handoff):
    admin       → system admin
    owner       → course ``_owner``
    maintainer  → course ``_maintainer``
    lecturer    → course ``_lecturer``
    tutor       → course ``_tutor``
    student     → course ``_student``
    anon        → unauthenticated

``_owner`` and ``_maintainer`` currently behave identically at the API
surface; they stay as separate columns so the matrix is ready when they
diverge.

Observed backend conventions (locked in by this matrix, not prescribed):
    - Unauthenticated requests to authed endpoints: **401**.
    - Reads across the hierarchy gate by visibility: any course member
      (including a student) sees the org/family/course they're enrolled
      in. Non-members see **404**. The seeded student is a member of the
      target course, so all read cells here are 200 for them; rows that
      probe a non-member scope would see 404.
    - Explicit permission denials on mutations return **403** for
      organization/course-family, **404** for course/lower scopes.
      This asymmetry is intentional to document.

Path templates may embed ``{course_id}``, ``{organization_id}``, and
``{course_family_id}``. Callers pass an ``ids`` dict sourced from the seed
fixtures through :func:`resolve_path`.

Cells marked ``UNSET`` are explicit "not yet asserted" placeholders so a
role test file can skip rows the matrix hasn't decided on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

UNSET = -1

ROLE_KEYS = ("admin", "owner", "maintainer", "lecturer", "tutor", "student", "anon")


@dataclass(frozen=True)
class MatrixRow:
    method: str
    path: str
    expected: dict[str, int] = field(default_factory=dict)
    body: dict[str, Any] | None = None

    def expected_for(self, role: str) -> int:
        return self.expected.get(role, UNSET)

    def id(self) -> str:
        return f"{self.method} {self.path}"


def _row(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    **expected: int,
) -> MatrixRow:
    unknown = set(expected) - set(ROLE_KEYS)
    assert not unknown, f"unknown role key(s): {unknown}"
    return MatrixRow(method=method, path=path, expected=dict(expected), body=body)


# Most authed endpoints share one of two permission shapes, so pull them
# out to keep the matrix literal readable.
_AUTHED_READ = dict(
    admin=200, owner=200, maintainer=200, lecturer=200, tutor=200, student=200, anon=401
)
_PUBLIC = dict(
    admin=200, owner=200, maintainer=200, lecturer=200, tutor=200, student=200, anon=200
)


MATRIX: tuple[MatrixRow, ...] = (
    # ---- Public ------------------------------------------------------
    _row("GET", "/auth/providers", **_PUBLIC),
    # ---- Whoami / self ----------------------------------------------
    _row("GET", "/user", **_AUTHED_READ),
    _row("GET", "/user/views", **_AUTHED_READ),
    # ---- Scope-filtered list reads (return 200 with a scope-filtered
    #      payload; authorization manifests as row visibility rather
    #      than a 4xx on the list endpoint itself) -----------------------
    _row("GET", "/users", **_AUTHED_READ),
    _row("GET", "/organizations", **_AUTHED_READ),
    _row("GET", "/course-families", **_AUTHED_READ),
    _row("GET", "/courses", **_AUTHED_READ),
    _row("GET", "/course-members", **_AUTHED_READ),
    # ---- Hierarchy detail reads (visibility-gated) --------------------
    _row("GET", "/organizations/{organization_id}", **_AUTHED_READ),
    _row("GET", "/course-families/{course_family_id}", **_AUTHED_READ),
    _row("GET", "/courses/{course_id}", **_AUTHED_READ),
    # ---- Lookup tables (any authed user) -----------------------------
    _row("GET", "/course-roles", **_AUTHED_READ),
    _row("GET", "/roles", **_AUTHED_READ),
    _row("GET", "/languages", **_AUTHED_READ),
    # ---- Personal resources (own tokens) -----------------------------
    _row("GET", "/api-tokens", **_AUTHED_READ),
    # ---- Role-discriminating mutations -------------------------------
    # Organization and course-family updates: admin-only; other authed
    # roles get 403 (explicit denial rather than visibility-based 404).
    _row(
        "PATCH",
        "/organizations/{organization_id}",
        body={},
        admin=200,
        owner=403,
        maintainer=403,
        lecturer=403,
        tutor=403,
        student=403,
        anon=401,
    ),
    _row(
        "PATCH",
        "/course-families/{course_family_id}",
        body={},
        admin=200,
        owner=403,
        maintainer=403,
        lecturer=403,
        tutor=403,
        student=403,
        anon=401,
    ),
    # Course update: anyone with _lecturer+ can update; tutor/student get
    # 404 (visibility pattern, matching the detail GETs above).
    _row(
        "PATCH",
        "/courses/{course_id}",
        body={},
        admin=200,
        owner=200,
        maintainer=200,
        lecturer=200,
        tutor=404,
        student=404,
        anon=401,
    ),
)


def resolve_path(row: MatrixRow, ids: dict[str, str]) -> str:
    """Substitute ``{course_id}`` etc. in a row's path template.

    Raises KeyError for missing keys so a typo in the matrix surfaces as
    a test-collection error rather than a silent 404 at runtime.
    """
    return row.path.format(**ids)


def call(
    client: httpx.Client, row: MatrixRow, ids: dict[str, str]
) -> httpx.Response:
    """Dispatch a matrix row against the given client."""
    kwargs: dict[str, Any] = {}
    if row.body is not None:
        kwargs["json"] = row.body
    return client.request(row.method, resolve_path(row, ids), **kwargs)


@pytest.fixture(scope="session")
def matrix_ids(
    target_organization: dict, target_course_family: dict, target_course: dict
) -> dict[str, str]:
    """The IDs used to materialise path-template placeholders."""
    return {
        "organization_id": target_organization["id"],
        "course_family_id": target_course_family["id"],
        "course_id": target_course["id"],
    }
