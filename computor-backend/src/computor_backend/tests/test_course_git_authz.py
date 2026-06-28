"""Authorization tests for course-level git management.

Pure predicate tests (no DB): ``is_registry_admin`` (registry = admin /
_organization_manager only) and ``can_manage_course_git`` (lecturer cohort),
plus the student_repo_modes DTO validator.
"""
from types import SimpleNamespace

import pytest

from computor_backend.business_logic.course_git import can_manage_course_git
from computor_backend.business_logic.git_registry import is_registry_admin
from computor_backend.permissions.principal import Principal, build_claims
from computor_types.course_git import CourseGitBindingUpsert


def _principal(roles=None, *claim_strings: str) -> Principal:
    return Principal(
        user_id="u-1",
        roles=list(roles or []),
        claims=build_claims([("permissions", c) for c in claim_strings]),
    )


def _course(org="o1", family="f1", cid="c1") -> SimpleNamespace:
    return SimpleNamespace(id=cid, organization_id=org, course_family_id=family)


class TestRegistryAdmin:
    def test_admin_allowed(self):
        assert is_registry_admin(_principal(["_admin"]))

    def test_organization_manager_allowed(self):
        assert is_registry_admin(_principal(["_organization_manager"]))

    def test_plain_user_denied(self):
        assert not is_registry_admin(_principal([]))

    def test_org_scope_role_does_not_grant_registry(self):
        # An organization _owner manages that org, but the registry holds service
        # credentials, so it stays admin/_organization_manager only.
        assert not is_registry_admin(_principal([], "organization:_owner:o1"))

    def test_course_lecturer_does_not_grant_registry(self):
        assert not is_registry_admin(_principal([], "course:_lecturer:c1"))


class TestCanManageCourseGit:
    def test_admin(self):
        assert can_manage_course_git(_principal(["_admin"]), _course())

    def test_organization_manager(self):
        assert can_manage_course_git(_principal(["_organization_manager"]), _course())

    def test_org_role_on_courses_org(self):
        assert can_manage_course_git(_principal([], "organization:_developer:o1"), _course(org="o1"))

    def test_org_role_on_other_org_denied(self):
        assert not can_manage_course_git(_principal([], "organization:_owner:other"), _course(org="o1"))

    def test_course_family_role_on_courses_family(self):
        assert can_manage_course_git(_principal([], "course_family:_manager:f1"), _course(family="f1"))

    def test_course_lecturer_allowed(self):
        assert can_manage_course_git(_principal([], "course:_lecturer:c1"), _course(cid="c1"))

    def test_course_owner_allowed(self):
        assert can_manage_course_git(_principal([], "course:_owner:c1"), _course(cid="c1"))

    def test_course_tutor_denied(self):
        assert not can_manage_course_git(_principal([], "course:_tutor:c1"), _course(cid="c1"))

    def test_course_student_denied(self):
        assert not can_manage_course_git(_principal([], "course:_student:c1"), _course(cid="c1"))

    def test_unrelated_user_denied(self):
        assert not can_manage_course_git(_principal([]), _course())


class TestModesValidator:
    def test_valid_modes_accepted(self):
        b = CourseGitBindingUpsert(student_repo_modes=["managed", "external", "download"])
        assert b.student_repo_modes == ["managed", "external", "download"]

    def test_invalid_mode_rejected(self):
        with pytest.raises(ValueError):
            CourseGitBindingUpsert(student_repo_modes=["managed", "bitbucket"])

    def test_empty_default(self):
        assert CourseGitBindingUpsert().student_repo_modes == []
