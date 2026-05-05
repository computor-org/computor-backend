"""Unit tests for the per-scope role API on ``Principal``.

Covers the generic ``has_scope_role`` / ``get_scoped_ids_with_role``
helpers and the back-compat course/organization/course_family wrappers
introduced for organization and course_family scoped roles.

The ``TestScopeMemberCustomPermissions`` block exercises the
``make_scope_member_custom_permissions`` factory used to plug an
update-payload-aware permission check into the CRUD layer for
OrganizationMember / CourseFamilyMember.

No DB. Pure ``Principal`` + claim-string round-tripping plus a small
in-memory SQLite session for the custom-permissions tests.
"""

from types import SimpleNamespace

import pytest
from sqlalchemy import Column, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from computor_backend.exceptions import ForbiddenException
from computor_backend.permissions.handlers_impl import (
    make_scope_member_custom_permissions,
)
from computor_backend.permissions.principal import (
    Principal,
    build_claims,
    organization_role_hierarchy,
    course_family_role_hierarchy,
    course_role_hierarchy,
    SCOPE_HIERARCHIES,
)


def _principal(*claim_strings: str) -> Principal:
    return Principal(
        user_id="u-1",
        claims=build_claims([("permissions", c) for c in claim_strings]),
    )


# ---------------------------------------------------------------------------
# Hierarchy semantics
# ---------------------------------------------------------------------------


class TestScopedHierarchies:
    def test_org_three_level_inclusion(self):
        h = organization_role_hierarchy
        # _owner satisfies every role in scope.
        assert h.has_role_permission("_owner", "_owner")
        assert h.has_role_permission("_owner", "_manager")
        assert h.has_role_permission("_owner", "_developer")
        # _manager satisfies _manager and _developer but not _owner.
        assert not h.has_role_permission("_manager", "_owner")
        assert h.has_role_permission("_manager", "_manager")
        assert h.has_role_permission("_manager", "_developer")
        # _developer is the lowest tier.
        assert not h.has_role_permission("_developer", "_owner")
        assert not h.has_role_permission("_developer", "_manager")
        assert h.has_role_permission("_developer", "_developer")

    def test_family_uses_same_hierarchy_shape(self):
        # We deliberately share the same hierarchy across org and family.
        h_org = organization_role_hierarchy
        h_fam = course_family_role_hierarchy
        for role in ("_owner", "_manager", "_developer"):
            assert h_org.get_allowed_roles(role) == h_fam.get_allowed_roles(role)

    def test_no_cross_scope_inheritance(self):
        # An organization claim does NOT grant a course_family or course role
        # on the same id, even with identical role names.
        p = _principal("organization:_owner:scope-1")
        assert p.has_organization_role("scope-1", "_owner")
        # course_family + course on the same id should NOT see it.
        assert not p.has_course_family_role("scope-1", "_developer")
        assert not p.has_course_role("scope-1", "_student")

    def test_scope_hierarchies_registry_contents(self):
        # Sanity: registry keys match the claim namespaces emitted by the
        # ``db_get_*_claims`` helpers and the prefixes used in the
        # ``<scope>:<role>:<id>`` claim format.
        assert set(SCOPE_HIERARCHIES) == {"course", "organization", "course_family"}
        assert SCOPE_HIERARCHIES["course"] is course_role_hierarchy
        assert SCOPE_HIERARCHIES["organization"] is organization_role_hierarchy
        assert SCOPE_HIERARCHIES["course_family"] is course_family_role_hierarchy


# ---------------------------------------------------------------------------
# build_claims + Principal end-to-end
# ---------------------------------------------------------------------------


class TestPrincipalScopedRoles:
    def test_owner_satisfies_all_lower_roles_on_same_scope(self):
        p = _principal("organization:_owner:o1")
        assert p.has_organization_role("o1", "_owner")
        assert p.has_organization_role("o1", "_manager")
        assert p.has_organization_role("o1", "_developer")

    def test_manager_does_not_satisfy_owner(self):
        p = _principal("organization:_manager:o2")
        assert not p.has_organization_role("o2", "_owner")
        assert p.has_organization_role("o2", "_manager")
        assert p.has_organization_role("o2", "_developer")

    def test_developer_only_satisfies_developer(self):
        p = _principal("organization:_developer:o3")
        assert not p.has_organization_role("o3", "_owner")
        assert not p.has_organization_role("o3", "_manager")
        assert p.has_organization_role("o3", "_developer")

    def test_unknown_scope_id_returns_false(self):
        p = _principal("organization:_owner:o1")
        assert not p.has_organization_role("o-not-mine", "_developer")

    def test_unknown_scope_returns_false(self):
        # ``has_scope_role`` must reject scopes not in SCOPE_HIERARCHIES.
        p = _principal("organization:_owner:o1")
        assert not p.has_scope_role("does-not-exist", "o1", "_owner")

    def test_admin_short_circuits_all_scope_checks(self):
        admin = Principal(user_id="a1", is_admin=True)
        assert admin.has_organization_role("anything", "_owner")
        assert admin.has_course_family_role("anything", "_owner")
        # ``get_scoped_ids_with_role`` returns an empty set for admins
        # (sentinel meaning "no filtering needed").
        assert admin.get_organizations_with_role("_owner") == set()


class TestGetScopedIdsWithRole:
    def test_collects_scopes_at_or_above_minimum(self):
        p = _principal(
            "organization:_owner:o1",
            "organization:_manager:o2",
            "organization:_developer:o3",
        )
        # Every id qualifies for >= _developer.
        assert p.get_organizations_with_role("_developer") == {"o1", "o2", "o3"}
        # Only _owner and _manager qualify for >= _manager.
        assert p.get_organizations_with_role("_manager") == {"o1", "o2"}
        # Only _owner qualifies for >= _owner.
        assert p.get_organizations_with_role("_owner") == {"o1"}

    def test_empty_when_principal_has_no_scope_claims(self):
        p = _principal("course:_lecturer:c1")  # course only
        assert p.get_organizations_with_role("_developer") == set()
        assert p.get_course_families_with_role("_developer") == set()

    def test_unknown_scope_returns_empty(self):
        p = _principal("organization:_owner:o1")
        assert p.get_scoped_ids_with_role("does-not-exist", "_owner") == set()


# ---------------------------------------------------------------------------
# Course-role back-compat — the existing helpers must still work after the
# refactor that delegates to the generic ``has_scope_role``.
# ---------------------------------------------------------------------------


class TestCourseBackCompat:
    def test_course_role_helpers_still_work(self):
        p = _principal("course:_lecturer:c1")
        assert p.has_course_role("c1", "_student")
        assert p.has_course_role("c1", "_lecturer")
        assert not p.has_course_role("c1", "_owner")

    def test_get_courses_with_role_uses_generic(self):
        p = _principal(
            "course:_lecturer:c1",
            "course:_student:c2",
        )
        assert p.get_courses_with_role("_student") == {"c1", "c2"}
        assert p.get_courses_with_role("_lecturer") == {"c1"}


# ---------------------------------------------------------------------------
# UPDATE-time custom permissions (the role-escalation guard)
# ---------------------------------------------------------------------------


class TestScopeMemberCustomPermissions:
    """Cover ``make_scope_member_custom_permissions`` against a fake model.

    A tiny SQLAlchemy declarative model on an in-memory SQLite database
    stands in for ``OrganizationMember`` / ``CourseFamilyMember`` — the
    helper is generic over scope, so any model with ``id``, scope_fk
    and role_fk columns exercises the same code path.
    """

    @pytest.fixture
    def session_with_member(self):
        Base = declarative_base()

        class FakeMember(Base):
            __tablename__ = "fake_member"
            id = Column(String, primary_key=True)
            scope_id = Column(String, nullable=False)
            role_id = Column(String, nullable=False)

        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        # Two existing rows on the same scope: one developer, one owner.
        db.add(FakeMember(id="row-dev", scope_id="o1", role_id="_developer"))
        db.add(FakeMember(id="row-owner", scope_id="o1", role_id="_owner"))
        db.commit()

        custom_permissions = make_scope_member_custom_permissions(
            FakeMember,
            scope="organization",
            scope_fk="scope_id",
            role_fk="role_id",
        )

        try:
            yield db, FakeMember, custom_permissions
        finally:
            db.close()

    def test_admin_passes_through(self, session_with_member):
        db, FakeMember, custom = session_with_member
        admin = Principal(user_id="a1", is_admin=True)
        # Promoting a developer to _owner is allowed for admin.
        payload = SimpleNamespace(role_id="_owner")
        q = custom(admin, db, "row-dev", payload)
        # Returned query reaches both rows (filtering to id happens later).
        assert q.count() == 2

    def test_manager_can_edit_developer_to_manager(self, session_with_member):
        db, FakeMember, custom = session_with_member
        mgr = _principal("organization:_manager:o1")
        payload = SimpleNamespace(role_id="_manager")
        # Should succeed — manager promoting developer to manager is OK.
        q = custom(mgr, db, "row-dev", payload)
        assert q is not None

    def test_manager_cannot_promote_to_owner(self, session_with_member):
        db, FakeMember, custom = session_with_member
        mgr = _principal("organization:_manager:o1")
        payload = SimpleNamespace(role_id="_owner")
        with pytest.raises(ForbiddenException):
            custom(mgr, db, "row-dev", payload)

    def test_manager_cannot_modify_owner_row(self, session_with_member):
        db, FakeMember, custom = session_with_member
        mgr = _principal("organization:_manager:o1")
        payload = SimpleNamespace(role_id="_developer")
        # Even if the new role is harmless, manager cannot touch an _owner row.
        with pytest.raises(ForbiddenException):
            custom(mgr, db, "row-owner", payload)

    def test_owner_can_promote_to_owner(self, session_with_member):
        db, FakeMember, custom = session_with_member
        owner = _principal("organization:_owner:o1")
        payload = SimpleNamespace(role_id="_owner")
        q = custom(owner, db, "row-dev", payload)
        assert q is not None

    def test_owner_can_modify_owner_row(self, session_with_member):
        db, FakeMember, custom = session_with_member
        owner = _principal("organization:_owner:o1")
        payload = SimpleNamespace(role_id="_manager")
        q = custom(owner, db, "row-owner", payload)
        assert q is not None

    def test_developer_blocked_outright(self, session_with_member):
        db, FakeMember, custom = session_with_member
        dev = _principal("organization:_developer:o1")
        payload = SimpleNamespace(role_id="_developer")
        with pytest.raises(ForbiddenException):
            custom(dev, db, "row-dev", payload)

    def test_principal_with_no_scope_role_blocked(self, session_with_member):
        db, FakeMember, custom = session_with_member
        outsider = _principal("organization:_owner:other-scope")
        payload = SimpleNamespace(role_id="_developer")
        with pytest.raises(ForbiddenException):
            custom(outsider, db, "row-dev", payload)

    def test_missing_row_returns_empty_query(self, session_with_member):
        db, FakeMember, custom = session_with_member
        admin = Principal(user_id="a", is_admin=True)
        # Non-existent id — handler returns an empty query rather than raising
        # so the CRUD layer can yield NotFoundException.
        q = custom(admin, db, "nope", SimpleNamespace(role_id="_owner"))
        assert q.count() == 2  # admin shortcut returns full query unchanged
        # And for a non-admin, the row-not-found path yields empty:
        mgr = _principal("organization:_manager:o1")
        q = custom(mgr, db, "nope", SimpleNamespace(role_id="_developer"))
        assert q.first() is None

    def test_payload_without_role_change_still_checks_current_role(
        self, session_with_member
    ):
        # A manager touching an _owner row without changing the role must
        # still be blocked — the row-restriction rule applies regardless of
        # whether the payload includes a role change.
        db, FakeMember, custom = session_with_member
        mgr = _principal("organization:_manager:o1")
        payload = SimpleNamespace()  # no role_id attribute
        with pytest.raises(ForbiddenException):
            custom(mgr, db, "row-owner", payload)
