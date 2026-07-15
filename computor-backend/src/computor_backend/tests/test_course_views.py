"""Unit tests for ``get_course_views_for_user``.

The ``lecturer`` view is the org → course-family → course *creation
pipeline* (not "lecturer of a single course"), so it must be granted to
anyone who can create or manage any of those scopes:

  * global ``_admin`` or ``_organization_manager``,
  * any organization-scoped role (``_owner``/``_manager``/``_developer``),
  * any course-family-scoped role,
  * a course role of ``_lecturer`` or higher.

The function is a pure projection of the already-resolved ``Principal`` —
no DB — so these tests construct principals from claim strings directly.
"""

from typing import List, Optional

from computor_backend.business_logic.users import get_course_views_for_user
from computor_backend.permissions.principal import Principal, build_claims


def _principal(roles: Optional[List[str]] = None, *claim_strings: str) -> Principal:
    return Principal(
        user_id="u-1",
        roles=list(roles or []),
        claims=build_claims([("permissions", c) for c in claim_strings]),
    )


class TestLecturerPipelineView:
    def test_admin_always_gets_lecturer(self):
        # Admins now also carry the user_manager view alongside lecturer.
        assert get_course_views_for_user(_principal(["_admin"])) == ["lecturer", "user_manager"]

    def test_organization_manager_gets_lecturer(self):
        assert get_course_views_for_user(
            _principal(["_organization_manager"])
        ) == ["lecturer"]

    def test_example_manager_gets_lecturer(self):
        # _example_manager owns the example library, which lives under the
        # lecturer authoring surface in the clients (the VS Code example tree
        # is gated on this view) — without it the role could not author.
        assert get_course_views_for_user(
            _principal(["_example_manager"])
        ) == ["lecturer"]

    def test_any_organization_role_gets_lecturer(self):
        for role in ("_owner", "_manager", "_developer"):
            views = get_course_views_for_user(
                _principal([], f"organization:{role}:o1")
            )
            assert views == ["lecturer"], role

    def test_any_course_family_role_gets_lecturer(self):
        for role in ("_owner", "_manager", "_developer"):
            views = get_course_views_for_user(
                _principal([], f"course_family:{role}:f1")
            )
            assert views == ["lecturer"], role

    def test_course_lecturer_or_higher_gets_lecturer(self):
        for role in ("_lecturer", "_maintainer", "_owner"):
            views = get_course_views_for_user(_principal([], f"course:{role}:c1"))
            # Elevated course roles see the full stack.
            assert views == ["lecturer", "student", "tutor"], role


class TestNonLecturerRoles:
    def test_student_only_sees_student(self):
        assert get_course_views_for_user(
            _principal([], "course:_student:c1")
        ) == ["student"]

    def test_tutor_sees_student_and_tutor_not_lecturer(self):
        assert get_course_views_for_user(
            _principal([], "course:_tutor:c1")
        ) == ["student", "tutor"]

    def test_user_manager_role_maps_to_user_manager_view(self):
        assert get_course_views_for_user(
            _principal(["_user_manager"])
        ) == ["user_manager"]

    def test_no_roles_yields_no_views(self):
        assert get_course_views_for_user(_principal()) == []


class TestCombinations:
    def test_org_role_plus_student_course(self):
        # Org role → lecturer; student membership → student. No tutor.
        assert get_course_views_for_user(
            _principal([], "organization:_owner:o1", "course:_student:c2")
        ) == ["lecturer", "student"]

    def test_user_manager_plus_org_role(self):
        assert get_course_views_for_user(
            _principal(["_user_manager"], "organization:_developer:o1")
        ) == ["lecturer", "user_manager"]

    def test_views_are_deduplicated_and_sorted(self):
        # Two lecturer sources + a tutor course must not duplicate "lecturer".
        views = get_course_views_for_user(
            _principal(
                ["_organization_manager"],
                "organization:_owner:o1",
                "course:_tutor:c1",
            )
        )
        assert views == ["lecturer", "student", "tutor"]
        assert len(views) == len(set(views))
