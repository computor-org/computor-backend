"""The creator of a course owns it (issue #386).

Covers ``business_logic.course_ownership.enroll_course_creator_as_owner`` and
the wiring that makes ``POST /courses`` run it. The rule has exactly one
exception — the deployment's bootstrap administrator — and that exception is
NOT "admins are skipped": a human administrator who creates a course is its
owner like anyone else.
"""

from types import SimpleNamespace

from computor_backend.business_logic.course_ownership import (
    enroll_course_creator_as_owner,
)
from computor_backend.interfaces.course import CourseInterface
from computor_backend.model.auth import User
from computor_backend.model.course import CourseMember
from computor_backend.utils.bootstrap_admin import BOOTSTRAP_ADMIN_PROP


class _FakeQuery:
    """Returns a canned row; the filter expression is built but not evaluated."""

    def __init__(self, row):
        self._row = row

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._row


class _FakeSession:
    """Answers ``query(User)`` and ``query(CourseMember)`` from fixed rows."""

    def __init__(self, user=None, member=None):
        self._rows = {User: user, CourseMember: member}
        self.added = []
        self.flushed = 0

    def query(self, model):
        return _FakeQuery(self._rows.get(model))

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        self.flushed += 1


def _course(created_by="user-1"):
    return SimpleNamespace(id="course-1", created_by=created_by)


def _user(**props):
    return User(id="user-1", properties=props or {})


def test_creator_becomes_owner():
    db = _FakeSession(user=_user())

    member = enroll_course_creator_as_owner(_course(), db)

    assert member is not None
    assert db.added == [member]
    assert db.flushed == 1
    assert member.user_id == "user-1"
    assert member.course_id == "course-1"
    assert member.course_role_id == "_owner"
    # The creator is also the audit author of their own membership.
    assert member.created_by == "user-1"
    assert member.updated_by == "user-1"


def test_owner_carries_no_course_group():
    """Only ``_student`` rows require a group (course_member check constraint)."""
    db = _FakeSession(user=_user())

    member = enroll_course_creator_as_owner(_course(), db)

    assert member.course_group_id is None


def test_bootstrap_admin_is_not_enrolled():
    db = _FakeSession(user=_user(**{BOOTSTRAP_ADMIN_PROP: True}))

    assert enroll_course_creator_as_owner(_course(), db) is None
    assert db.added == []


def test_plain_admin_is_still_enrolled():
    """``_admin`` is not the exception — only the one bootstrap account is."""
    db = _FakeSession(user=_user(some_other_flag=True))

    member = enroll_course_creator_as_owner(_course(), db)

    assert member is not None
    assert member.course_role_id == "_owner"


def test_existing_membership_is_left_alone():
    """Idempotent: re-applying a deployment must not duplicate or demote."""
    existing = CourseMember(
        user_id="user-1", course_id="course-1", course_role_id="_lecturer"
    )
    db = _FakeSession(user=_user(), member=existing)

    assert enroll_course_creator_as_owner(_course(), db) is None
    assert db.added == []


def test_no_creator_is_a_noop():
    db = _FakeSession(user=_user())

    assert enroll_course_creator_as_owner(_course(created_by=None), db) is None
    assert db.added == []


def test_explicit_user_id_wins_over_created_by():
    """The Temporal activity knows the acting user; audit columns may not be set."""
    db = _FakeSession(user=_user())

    member = enroll_course_creator_as_owner(
        _course(created_by=None), db, user_id="user-1"
    )

    assert member is not None
    assert member.user_id == "user-1"


def test_post_create_hook_is_wired():
    """Without this the CRUD path silently creates course-less lecturers again."""
    assert CourseInterface.post_create is not None
    # Creating a course changes the caller's own authorization, so the route
    # must drop their cached Principal (CrudRouter._invalidate_creator_principal).
    assert CourseInterface.grants_creator_scope_role is True
