"""Who may open a course for self-registration (issue #213).

``public`` is held above the ``_lecturer`` bar that every other course setting
sits on: it advertises the course to every account on the deployment and lets
strangers enrol themselves. These tests pin that split, and — just as
importantly — pin that a lecturer did NOT lose the ability to edit everything
else, since the guard replaces ``check_permissions`` on the whole update path.
"""

import uuid

import pytest

from computor_backend.exceptions import ForbiddenException
from computor_backend.interfaces.course import custom_permissions_course
from computor_backend.permissions.principal import Claims, Principal
from computor_types.courses import CourseUpdate


COURSE_ID = str(uuid.uuid4())


def _principal(course_role: str | None = None, *, is_admin=False, roles=None) -> Principal:
    """A principal holding one course role in COURSE_ID."""
    dependent = {}
    if course_role:
        dependent = {"course": {COURSE_ID: {course_role}}}
    return Principal(
        user_id=str(uuid.uuid4()),
        is_admin=is_admin,
        roles=roles or [],
        claims=Claims(general={}, dependent=dependent),
    )


class _Query:
    def filter(self, *a, **k):
        return self


class _Session:
    """check_permissions only needs .query() to hand back something chainable."""

    def query(self, *a, **k):
        return _Query()


@pytest.mark.parametrize("role", ["_student", "_tutor", "_lecturer"])
def test_roles_below_maintainer_cannot_change_public(role):
    with pytest.raises(ForbiddenException) as exc:
        custom_permissions_course(
            _principal(role), _Session(), COURSE_ID, CourseUpdate(public=True)
        )
    assert exc.value.error_code == "AUTHZ_004"


@pytest.mark.parametrize("role", ["_maintainer", "_owner"])
def test_maintainer_and_owner_can_change_public(role):
    # Does not raise. The returned query is check_permissions' own.
    custom_permissions_course(
        _principal(role), _Session(), COURSE_ID, CourseUpdate(public=True)
    )


def test_admin_and_organization_manager_can_change_public():
    custom_permissions_course(
        _principal(is_admin=True), _Session(), COURSE_ID, CourseUpdate(public=True)
    )
    custom_permissions_course(
        _principal(roles=["_organization_manager"]),
        _Session(),
        COURSE_ID,
        CourseUpdate(public=True),
    )


def test_a_non_member_cannot_change_public():
    with pytest.raises(ForbiddenException):
        custom_permissions_course(
            _principal(), _Session(), COURSE_ID, CourseUpdate(public=True)
        )


def test_closing_a_course_is_guarded_too():
    """Un-listing is the same institutional decision as listing."""
    with pytest.raises(ForbiddenException):
        custom_permissions_course(
            _principal("_lecturer"), _Session(), COURSE_ID, CourseUpdate(public=False)
        )


def test_a_lecturer_can_still_edit_every_other_field():
    """The regression guard for replacing check_permissions wholesale."""
    custom_permissions_course(
        _principal("_lecturer"),
        _Session(),
        COURSE_ID,
        CourseUpdate(title="New title", visible=False, max_submissions=3),
    )


def test_an_update_that_omits_public_is_not_guarded():
    """exclude_unset semantics: only an explicitly sent key is a change.

    A client that round-trips a CourseGet into a CourseUpdate would otherwise
    trip the guard on every save without ever touching the flag.
    """
    update = CourseUpdate(title="Renamed")
    assert "public" not in update.model_fields_set

    custom_permissions_course(_principal("_lecturer"), _Session(), COURSE_ID, update)
