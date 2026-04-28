"""Unit tests for ``GET /user/scopes`` projection.

The endpoint is a pure transformation of ``Principal.claims`` into the
``UserScopes`` DTO — no DB access, no auth machinery. We exercise the
projection helper directly across the cases a client will care about:

- non-admin with various scope claims
- admin (empty maps + ``is_admin=True`` sentinel)
- a principal carrying claims on namespaces *outside* the registered
  scope hierarchies (those must be silently dropped — only the three
  client-relevant namespaces are surfaced)
- multi-role-per-scope (a user with two roles on the same org)

The role lists are sorted on the way out so the response is stable and
diff-friendly for snapshot-style consumers.
"""

import pytest

from computor_backend.business_logic.users import get_user_scopes_from_principal
from computor_backend.permissions.principal import Principal, build_claims
from computor_types.users import UserScopes


def _principal(*claim_strings: str, is_admin: bool = False) -> Principal:
    return Principal(
        user_id="u-1",
        is_admin=is_admin,
        claims=build_claims([("permissions", c) for c in claim_strings]),
    )


class TestUserScopesProjection:
    def test_admin_returns_empty_maps_with_flag(self):
        scopes = get_user_scopes_from_principal(_principal(is_admin=True))
        assert isinstance(scopes, UserScopes)
        assert scopes.is_admin is True
        assert scopes.organization == {}
        assert scopes.course_family == {}
        assert scopes.course == {}

    def test_organization_claim_surfaced(self):
        scopes = get_user_scopes_from_principal(
            _principal("organization:_owner:o1")
        )
        assert scopes.is_admin is False
        assert scopes.organization == {"o1": ["_owner"]}
        assert scopes.course_family == {}
        assert scopes.course == {}

    def test_course_family_claim_surfaced(self):
        scopes = get_user_scopes_from_principal(
            _principal("course_family:_manager:f1")
        )
        assert scopes.course_family == {"f1": ["_manager"]}

    def test_course_claim_surfaced(self):
        scopes = get_user_scopes_from_principal(
            _principal("course:_lecturer:c1")
        )
        assert scopes.course == {"c1": ["_lecturer"]}

    def test_mixed_scopes(self):
        scopes = get_user_scopes_from_principal(
            _principal(
                "organization:_owner:o1",
                "organization:_manager:o2",
                "course_family:_owner:f1",
                "course:_lecturer:c1",
                "course:_student:c2",
            )
        )
        assert scopes.organization == {"o1": ["_owner"], "o2": ["_manager"]}
        assert scopes.course_family == {"f1": ["_owner"]}
        assert scopes.course == {"c1": ["_lecturer"], "c2": ["_student"]}

    def test_multiple_roles_on_same_scope_sorted(self):
        # A user can hold more than one role on the same scope; the
        # response sorts them so the ordering is deterministic for
        # snapshot tests on the client side.
        scopes = get_user_scopes_from_principal(
            _principal(
                "organization:_owner:o1",
                "organization:_developer:o1",
                "organization:_manager:o1",
            )
        )
        assert scopes.organization == {
            "o1": ["_developer", "_manager", "_owner"],
        }

    def test_unknown_scope_namespaces_dropped(self):
        # Only the three currently-registered namespaces are surfaced;
        # any future or legacy claim namespace stays internal.
        scopes = get_user_scopes_from_principal(
            _principal(
                "organization:_owner:o1",
                "submission_group:_member:sg1",  # not a scope hierarchy
            )
        )
        assert scopes.organization == {"o1": ["_owner"]}
        assert scopes.course_family == {}
        assert scopes.course == {}

    def test_principal_with_no_claims(self):
        # A bare principal with no claims at all is valid (e.g. a brand-new
        # account before any membership is granted).
        scopes = get_user_scopes_from_principal(Principal(user_id="u-1"))
        assert scopes.is_admin is False
        assert scopes.organization == {}
        assert scopes.course_family == {}
        assert scopes.course == {}
