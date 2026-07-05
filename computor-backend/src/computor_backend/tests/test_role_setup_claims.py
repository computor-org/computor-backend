"""Regression tests for role-claim setup.

The ``_organization_manager`` role grants global management permissions
on a set of parent entities (Organization, CourseFamily, Course,
Example, Extension). When the scoped-member tables landed (PR #112)
they introduced new CRUD endpoints — ``/organization-members`` and
``/course-family-members`` — but the manager's claim set wasn't
extended to match. CrudRouter found no permitting handler and
fell through to the admin-only NotFoundException → 404.

The fix adds the two missing ``claim_values()`` calls. These tests
guard against the regression returning if either:

- a future refactor narrows ``claims_organization_manager`` again, or
- a new scoped-member entity is added without being wired in.

Pure unit — no DB, no auth machinery, just call the function.
"""

import pytest

from computor_backend.permissions.role_setup import (
    claims_example_manager,
    claims_organization_manager,
)


def _claims_by_entity():
    """Return ``{entity_name: [claim_strings]}`` from the manager
    role's claim values. ``claim_values()`` yields
    ``("permissions", "<entity>:<action>")`` tuples."""
    by_entity: dict[str, list[str]] = {}
    for claim_type, claim in claims_organization_manager():
        assert claim_type == "permissions", (
            f"unexpected claim type {claim_type!r}"
        )
        entity = claim.split(":", 1)[0]
        by_entity.setdefault(entity, []).append(claim)
    return by_entity


class TestOrganizationManagerClaims:
    """Every entity the role is supposed to manage is represented in
    the claim set with at least the standard CRUD verbs."""

    @pytest.mark.parametrize("entity", [
        "organization",
        "course_family",
        "course",
        "example",
        # ExampleRepository is its own CrudRouter resource; the ``example:*``
        # claims don't cover it, so managers 403'd on the examples repository
        # page until it was wired in.
        "example_repository",
        "extension",
        # The two that were missing — the regression we're guarding against.
        "organization_member",
        "course_family_member",
    ])
    def test_entity_present(self, entity):
        assert entity in _claims_by_entity(), (
            f"{entity} is not in the _organization_manager claim set — "
            "managers will get 404 on its CRUD endpoints"
        )

    @pytest.mark.parametrize("entity,action", [
        ("organization_member", "create"),
        ("organization_member", "list"),
        ("organization_member", "get"),
        ("organization_member", "update"),
        ("course_family_member", "create"),
        ("course_family_member", "list"),
        ("course_family_member", "get"),
        ("course_family_member", "update"),
    ])
    def test_member_table_crud_actions_granted(self, entity, action):
        # The exact action that triggered the bug report was POST
        # ``/organization-members`` (= ``create``). We assert all four
        # standard verbs so a future trim of the interface's
        # ``claim_values()`` can't silently drop one.
        claims = _claims_by_entity().get(entity, [])
        assert f"{entity}:{action}" in claims, (
            f"{entity}:{action} missing from manager claims"
        )

    @pytest.mark.parametrize("claim", [
        # The examples pages list (``list``), open (``get``), and download
        # examples. ExamplePermissionHandler checks the per-entity tablename,
        # so ``example_repository`` reads must be present independently of the
        # ``example:*`` reads.
        "example:get",
        "example:list",
        "example:download",
        "example_repository:get",
        "example_repository:list",
    ])
    def test_example_read_claims_granted(self, claim):
        entity = claim.split(":", 1)[0]
        claims = _claims_by_entity().get(entity, [])
        assert claim in claims, (
            f"{claim} missing from manager claims — managers must retain "
            "read access to the example library"
        )

    @pytest.mark.parametrize("claim", [
        # Authoring the example library is reserved to ``_example_manager``.
        # The manager keeps read access only (see test above).
        "example:create",
        "example:update",
        "example:upload",
        "example:delete",
        "example_repository:create",
        "example_repository:update",
        "example_repository:delete",
    ])
    def test_example_authoring_claims_revoked(self, claim):
        entity = claim.split(":", 1)[0]
        claims = _claims_by_entity().get(entity, [])
        assert claim not in claims, (
            f"{claim} is granted to _organization_manager — example authoring "
            "must be reserved to the _example_manager role"
        )

    def test_no_duplicate_member_claims(self):
        # Defensive: if both ``OrganizationMemberInterface`` and the
        # legacy parent extends ever accidentally double-add member
        # rows, the role table inflates.
        all_claims = list(claims_organization_manager())
        for prefix in ("organization_member:", "course_family_member:"):
            member_claims = [c for _, c in all_claims if c.startswith(prefix)]
            assert len(member_claims) == len(set(member_claims)), (
                f"duplicate claims under {prefix!r} — likely an "
                f"accidental double-extend in role_setup.py"
            )


class TestExampleManagerClaims:
    """``_example_manager`` owns the full example-authoring surface, and no
    other role may (org managers and lecturers are read-only)."""

    @staticmethod
    def _claims():
        return {c for _, c in claims_example_manager()}

    @pytest.mark.parametrize("claim", [
        "example:get",
        "example:list",
        "example:download",
        "example:create",
        "example:update",
        "example:upload",
        "example:delete",
        "example_repository:get",
        "example_repository:list",
        "example_repository:create",
        "example_repository:update",
        "example_repository:delete",
    ])
    def test_manager_grants_full_example_surface(self, claim):
        assert claim in self._claims(), (
            f"{claim} missing from _example_manager — the role must cover the "
            "whole example-authoring surface"
        )

    def test_only_permissions_claim_type(self):
        for claim_type, _ in claims_example_manager():
            assert claim_type == "permissions", (
                f"unexpected claim type {claim_type!r} in _example_manager"
            )

    def test_no_duplicate_claims(self):
        all_claims = [c for _, c in claims_example_manager()]
        assert len(all_claims) == len(set(all_claims)), (
            "duplicate claims in claims_example_manager()"
        )
