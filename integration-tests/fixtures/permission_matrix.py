"""RBAC permission matrix: one row per ``(method, path)`` with per-persona
expected HTTP status codes.

Lives under ``fixtures/`` so the test files in ``suites/03_permissions/`` can
import it (suite dirs start with a digit → not importable as packages).

Persona columns (see ``fixtures.personas``):
    admin    → system ``_admin`` (bypasses every check)
    uma      → ``_user_manager``
    orga     → ``_organization_manager``
    exma     → ``_example_manager``
    lena     → course ``_lecturer``
    tobi     → course ``_tutor``
    student  → course ``_student`` (s_correct)
    anon     → unauthenticated

Expected statuses are **characterized** against the running backend (probe →
calibrate), so this matrix documents the real conventions rather than an
idealized one. Observed conventions locked in here:
    - Unauthenticated → **401** on every authed endpoint.
    - List reads are scope-filtered: **200** for any authed persona (payload
      differs), authorization shows up as row visibility, not a 4xx.
    - Example reads are claim-gated: only admin / example-manager / org-manager
      (read-only) / lecturer see them; uma / tutor / student → **403**.
    - Hierarchy detail reads gate by visibility: admin, org-manager and course
      members (lecturer/tutor/student) → 200; non-members (uma/exma) → **404**.
    - Course-git-binding reads are lecturer-cohort only (admin/orga/lecturer);
      others → **403**.
    - Mutations: org/family/course updates are admin + org-manager (course also
      lecturer); everyone else → **404** (existence hidden on write even where the
      read is 200). Invite creation is admin + user-manager (others 403). The
      course role-assignment ceiling: a lecturer seating a ``_tutor`` → **403**.

``UNSET`` cells are deliberately-unasserted (e.g. an authorized POST we don't
want to fire because it mutates or 500s); the per-persona test skips them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

UNSET = -1

ROLE_KEYS = ("admin", "uma", "orga", "exma", "lena", "tobi", "student", "anon")


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


def _row(method: str, path: str, body: dict[str, Any] | None = None, **expected: int) -> MatrixRow:
    unknown = set(expected) - set(ROLE_KEYS)
    assert not unknown, f"unknown role key(s): {unknown}"
    return MatrixRow(method=method, path=path, expected=dict(expected), body=body)


def _all(**overrides: int) -> dict[str, int]:
    """Every authed persona 200, anon 401, with per-persona overrides."""
    base = {k: 200 for k in ROLE_KEYS if k != "anon"}
    base["anon"] = 401
    base.update(overrides)
    return base


_AUTHED_READ = _all()  # all authed 200, anon 401
_PUBLIC = {k: 200 for k in ROLE_KEYS}


MATRIX: tuple[MatrixRow, ...] = (
    # ---- Public -------------------------------------------------------
    _row("GET", "/auth/providers", **_PUBLIC),
    # ---- Authed list reads / lookups (scope-filtered → 200) -----------
    _row("GET", "/user", **_AUTHED_READ),
    _row("GET", "/users", **_AUTHED_READ),
    _row("GET", "/organizations", **_AUTHED_READ),
    _row("GET", "/course-families", **_AUTHED_READ),
    _row("GET", "/courses", **_AUTHED_READ),
    _row("GET", "/course-members", **_AUTHED_READ),
    _row("GET", "/course-roles", **_AUTHED_READ),
    _row("GET", "/roles", **_AUTHED_READ),
    _row("GET", "/languages", **_AUTHED_READ),
    _row("GET", "/api-tokens", **_AUTHED_READ),
    _row("GET", "/git-servers", **_AUTHED_READ),
    # ---- Example reads (claim-gated) ----------------------------------
    _row("GET", "/examples", **_all(uma=403, tobi=403, student=403)),
    # ---- Hierarchy detail reads (visibility-gated) --------------------
    _row("GET", "/organizations/{organization_id}", **_all(uma=404, exma=404)),
    _row("GET", "/course-families/{course_family_id}", **_all(uma=404, exma=404)),
    _row("GET", "/courses/{course_id}", **_all(uma=404, exma=404)),
    # ---- Course git binding read (lecturer cohort only) ---------------
    _row("GET", "/courses/{course_id}/git", **_all(uma=403, exma=403, tobi=403, student=403)),
    # ---- Idempotent mutations (PATCH {}) ------------------------------
    # org/family: admin + org-manager only; everyone else 404 (hidden on write).
    _row("PATCH", "/organizations/{organization_id}", body={},
         **_all(uma=404, exma=404, lena=404, tobi=404, student=404)),
    _row("PATCH", "/course-families/{course_family_id}", body={},
         **_all(uma=404, exma=404, lena=404, tobi=404, student=404)),
    # course: admin + org-manager + lecturer; tutor/student/others 404.
    _row("PATCH", "/courses/{course_id}", body={},
         **_all(uma=404, exma=404, tobi=404, student=404)),
    # ---- Invite creation (admin + user-manager) -----------------------
    _row("POST", "/admin/invites", body={"max_uses": 1, "expires_in_days": 7, "roles": []},
         admin=201, uma=201, orga=403, exma=403, lena=403, tobi=403, student=403, anon=401),
    # ---- Denial-only rows (authorized cell UNSET — would mutate) -------
    # git-server create: everyone but admin/org-manager denied.
    _row("POST", "/git-servers",
         body={"type": "forgejo", "base_url": "http://example.invalid", "name": "matrix-probe"},
         uma=403, exma=403, lena=403, tobi=403, student=403, anon=401),
    # course-member seat _tutor: the ceiling — a lecturer is denied 403.
    _row("POST", "/course-members",
         body={"user_id": "{student_user_id}", "course_id": "{course_id}", "course_role_id": "_tutor"},
         lena=403, uma=404, exma=404, tobi=404, student=404, anon=401),
)


def resolve_path(row: MatrixRow, ids: dict[str, str]) -> str:
    return row.path.format(**ids)


def _resolve_body(body: dict[str, Any] | None, ids: dict[str, str]) -> dict[str, Any] | None:
    if not body:
        return body
    out: dict[str, Any] = {}
    for k, v in body.items():
        out[k] = v.format(**ids) if isinstance(v, str) and "{" in v else v
    return out


def call(client: httpx.Client, row: MatrixRow, ids: dict[str, str]) -> httpx.Response:
    kwargs: dict[str, Any] = {}
    if row.body is not None:
        kwargs["json"] = _resolve_body(row.body, ids)
    return client.request(row.method, resolve_path(row, ids), **kwargs)


def check_matrix_row(row, client, ids, role, record_property=None) -> None:
    """Shared assertion body; also records a ``matrix_observation`` for the report."""
    expected = row.expected_for(role)
    if expected == UNSET:
        pytest.skip(f"matrix cell not asserted for {role}")
    r = call(client, row, ids)
    if record_property is not None:
        record_property(
            "matrix_observation",
            {"role": role, "method": row.method, "path": row.path,
             "expected": expected, "observed": r.status_code},
        )
    assert r.status_code == expected, (
        f"{row.method} {r.request.url}: expected {expected}, got {r.status_code} — body={r.text[:200]}"
    )


@pytest.fixture(scope="session")
def matrix_ids(
    target_organization: dict,
    target_course_family: dict,
    target_course: dict,
    enrolled_students: dict,
) -> dict[str, str]:
    """IDs used to materialise path/body placeholders."""
    return {
        "organization_id": target_organization["id"],
        "course_family_id": target_course_family["id"],
        "course_id": target_course["id"],
        # a real user id for the ceiling row (already enrolled → the ceiling
        # 403/404 fires before any duplicate check, so it's a safe target).
        "student_user_id": enrolled_students["s_empty"]["user_id"],
    }


# ---------------------------------------------------------------------------
# P3.1 — OpenAPI inventory + coverage guard
#
# The guard (``suites/03_permissions/test_coverage_guard.py``) flags any live
# endpoint that is in neither ``MATRIX`` nor the exclusions below, so adding an
# endpoint forces a matrix-or-exclude decision. Exclusions are curated here.
# ---------------------------------------------------------------------------

# Path prefixes that are intentionally out of the permission matrix: public /
# plumbing / streaming routes, and features out of the integration test scope.
EXCLUDED_PREFIXES: tuple[str, ...] = (
    "/auth",            # SSO login/callback/logout — covered by 02_auth
    "/docs", "/redoc", "/openapi.json",  # API docs
    "/health", "/healthz", "/livez", "/readyz",  # liveness/readiness probes
    "/metrics",         # prometheus scrape
    "/ws",              # websocket routes (not REST authz)
    "/coder", "/workspace",  # Coder feature — excluded from scope (issue #106)
    "/consent",         # consent-gate middleware — its own concern
    "/results", "/tests",  # test-runner streaming/callbacks
)

# Exact (METHOD, path) escapes for anything not captured by a prefix.
EXCLUDED: frozenset[tuple[str, str]] = frozenset({
    ("GET", "/"),  # service root
})

_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def matrix_coverage() -> set[tuple[str, str]]:
    """The ``(METHOD, path)`` pairs the permission MATRIX already asserts."""
    return {(row.method.upper(), row.path) for row in MATRIX}


def is_excluded(method: str, path: str) -> bool:
    """True when ``(method, path)`` is intentionally outside the matrix."""
    if (method.upper(), path) in EXCLUDED:
        return True
    return any(path == p or path.startswith(p + "/") for p in EXCLUDED_PREFIXES)


@pytest.fixture(scope="session")
def openapi_inventory(admin_client: httpx.Client) -> set[tuple[str, str]]:
    """Every ``(METHOD, path)`` the live backend advertises in ``/openapi.json``."""
    resp = admin_client.get("/openapi.json")
    resp.raise_for_status()
    paths: dict[str, dict] = resp.json().get("paths", {})
    return {
        (method.upper(), path)
        for path, operations in paths.items()
        for method in operations
        if method.upper() in _HTTP_METHODS
    }
