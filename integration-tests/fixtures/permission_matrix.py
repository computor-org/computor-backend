"""RBAC permission matrix: one row per ``(method, path)`` with per-role
expected HTTP status codes.

Lives under ``fixtures/`` so the test files in ``suites/03_permissions/``
can import it cleanly (the suite directories are named with a leading
digit, which is not a valid Python package identifier, so normal relative
imports within ``suites/03_permissions/`` don't work).

This first milestone ships a curated slice (~15 rows) covering
representative endpoints — list + detail on the main hierarchy resources
plus a handful of always-admin-only endpoints. Later PRs will fill in more
rows as each role suite lands.

Column keys (handoff):
    admin       → system admin
    owner       → course ``_owner``
    maintainer  → course ``_maintainer``
    lecturer    → course ``_lecturer``
    tutor       → course ``_tutor``
    student     → course ``_student``
    anon        → unauthenticated

``_owner`` and ``_maintainer`` collapse into one functional column today
(same permissions); they stay as separate columns so the matrix is ready
when they diverge.

Path templates may embed ``{course_id}``, ``{organization_id}``, and
``{course_family_id}``. Callers pass an ``ids`` dict sourced from the seed
fixtures through :func:`resolve_path`.

Only the columns consumed by a given role's test file need to be correct;
cells marked ``UNSET`` are explicit "not yet asserted" placeholders so the
matrix stays dense without forcing speculation for roles we haven't tested
yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx
import pytest

UNSET = -1

ROLE_KEYS = ("admin", "owner", "maintainer", "lecturer", "tutor", "student", "anon")


@dataclass(frozen=True)
class MatrixRow:
    method: str
    path: str
    expected: dict[str, int] = field(default_factory=dict)

    def expected_for(self, role: str) -> int:
        return self.expected.get(role, UNSET)

    def id(self) -> str:
        return f"{self.method} {self.path}"


def _row(method: str, path: str, **expected: int) -> MatrixRow:
    unknown = set(expected) - set(ROLE_KEYS)
    assert not unknown, f"unknown role key(s): {unknown}"
    return MatrixRow(method=method, path=path, expected=dict(expected))


# ---- The matrix --------------------------------------------------------
#
# Conventions used below:
#   - List endpoints: admin=200, anon=401. Course-scoped roles TBD.
#   - Public endpoints (no auth required): admin=200, anon=200.
#   - Admin-only endpoints (no course-role equivalent): admin=200, other
#     authed roles tentatively 403, anon=401.

MATRIX: tuple[MatrixRow, ...] = (
    # Public — no auth required.
    _row("GET", "/auth/providers", admin=200, anon=200),
    # Whoami / current user.
    _row("GET", "/user", admin=200, anon=401),
    _row("GET", "/user/views", admin=200, anon=401),
    # User CRUD (admin-managed).
    _row("GET", "/users", admin=200, anon=401),
    # Organization / course-family / course list + detail.
    _row("GET", "/organizations", admin=200, anon=401),
    _row("GET", "/organizations/{organization_id}", admin=200, anon=401),
    _row("GET", "/course-families", admin=200, anon=401),
    _row("GET", "/course-families/{course_family_id}", admin=200, anon=401),
    _row("GET", "/courses", admin=200, anon=401),
    _row("GET", "/courses/{course_id}", admin=200, anon=401),
    # Course membership + lookup tables.
    _row("GET", "/course-members", admin=200, anon=401),
    _row("GET", "/course-roles", admin=200, anon=401),
    _row("GET", "/roles", admin=200, anon=401),
    _row("GET", "/languages", admin=200, anon=401),
    # Personal API tokens (list own).
    _row("GET", "/api-tokens", admin=200, anon=401),
)


def resolve_path(row: MatrixRow, ids: dict[str, str]) -> str:
    """Substitute ``{course_id}`` etc. in a row's path template.

    Raises KeyError for missing keys so a typo in the matrix shows up as a
    test collection error rather than a silent 404.
    """
    return row.path.format(**ids)


def call(
    client: httpx.Client, row: MatrixRow, ids: dict[str, str]
) -> httpx.Response:
    """Dispatch a matrix row against the given client."""
    return client.request(row.method, resolve_path(row, ids))


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
