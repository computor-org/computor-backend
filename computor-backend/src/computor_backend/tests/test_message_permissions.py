"""Unit tests for message scope permissions.

Covers ``business_logic.messages.create_message_with_author`` and the
per-scope write helpers it dispatches to. The goal is to verify the
scope rules end-to-end at the business-logic boundary:

+-----------------------+--------------------------------------------------+
| None (global)         | admin only on write (read is public; verified in |
|                       | the handler-side tests, not here)                |
| user_id               | NotImplementedException (path wired but disabled)|
| course_member_id      | NotImplementedException (not implemented yet)    |
| submission_group_id   | submission_group_member OR course role >= _tutor |
| course_content_id     | course role >= _lecturer                         |
| course_group_id       | course role >= _lecturer                         |
| course_id             | course role >= _lecturer                         |
| course_family_id      | scoped course_family role >= _manager (admin OK) |
| organization_id       | scoped organization role >= _manager (admin OK)  |
+-----------------------+--------------------------------------------------+

The dispatch tests monkeypatch the per-scope helpers so we can assert
which helper fires without booting a DB. The pure-rule tests for
organization / course_family / global don't touch the DB at all (the
helpers consult only ``Principal``).

Replies inherit the parent's target; we verify that and also that
non-primary target columns are explicitly nulled out (the single-target
invariant the read filter relies on).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from computor_backend.api.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotImplementedException,
)
from computor_backend.business_logic import messages as messages_bl
from computor_backend.business_logic.messages import (
    MESSAGE_TARGET_FIELDS,
    _check_course_family_write_permission,
    _check_global_write_permission,
    _check_organization_write_permission,
    _check_user_message_write_permission as _real_user_check,
    create_message_with_author,
)
from computor_backend.permissions.principal import Principal, build_claims


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _principal(*claim_strings: str, is_admin: bool = False, user_id: str = "u-1") -> Principal:
    return Principal(
        user_id=user_id,
        is_admin=is_admin,
        claims=build_claims([("permissions", c) for c in claim_strings]),
    )


def _payload(**fields):
    """Build a fake MessageCreate-shaped object.

    We don't need the real Pydantic model — ``create_message_with_author``
    only calls ``.content`` and ``.model_dump(exclude_unset=True)``. Using
    a SimpleNamespace keeps these tests free of the heavy DTO module.
    """

    fields.setdefault("content", "hello")

    class _Fake(SimpleNamespace):
        def model_dump(self, exclude_unset: bool = False):
            data = dict(self.__dict__)
            if exclude_unset:
                data = {k: v for k, v in data.items() if v is not None}
            return data

    return _Fake(**fields)


def _stub_helpers(monkeypatch):
    """Replace every per-scope helper with a no-op MagicMock.

    Returns the dict of mocks so a test can assert which one fired.
    """

    mocks = {
        name: MagicMock(name=name, return_value=None)
        for name in (
            "_check_global_write_permission",
            "_check_user_message_write_permission",
            "_check_submission_group_write_permission",
            "_check_course_content_write_permission",
            "_check_course_group_write_permission",
            "_check_course_write_permission",
            "_check_course_family_write_permission",
            "_check_organization_write_permission",
        )
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(messages_bl, name, mock)
    return mocks


# ---------------------------------------------------------------------------
# Pure-rule tests: helpers that don't touch the DB
# ---------------------------------------------------------------------------


class TestGlobalScope:
    def test_admin_can_post_global(self):
        admin = _principal(is_admin=True)
        # Should not raise.
        _check_global_write_permission(admin)

    def test_non_admin_blocked(self):
        user = _principal("organization:_owner:o1")  # high org role still not enough
        with pytest.raises(ForbiddenException):
            _check_global_write_permission(user)

    def test_non_admin_blocked_via_create(self):
        user = _principal("course:_owner:c1")
        with pytest.raises(ForbiddenException):
            create_message_with_author(_payload(), user, db=MagicMock())

    def test_admin_create_global_succeeds(self, monkeypatch):
        mocks = _stub_helpers(monkeypatch)
        admin = _principal(is_admin=True)
        # No targets and no parent — global scope; admin path is allowed.
        # Bypass the stubbed _check_global_write_permission and verify it
        # got called.
        result = create_message_with_author(_payload(), admin, db=MagicMock())
        mocks["_check_global_write_permission"].assert_called_once_with(admin)
        # Every target column must be NULL on a global row.
        for f in MESSAGE_TARGET_FIELDS:
            assert result.get(f) is None


class TestOrganizationScope:
    def test_owner_allowed(self):
        p = _principal("organization:_owner:o1")
        _check_organization_write_permission(p, "o1")  # no raise

    def test_manager_allowed(self):
        p = _principal("organization:_manager:o1")
        _check_organization_write_permission(p, "o1")

    def test_developer_blocked(self):
        # Per product decision, _developer is below the bar for org messages.
        p = _principal("organization:_developer:o1")
        with pytest.raises(ForbiddenException):
            _check_organization_write_permission(p, "o1")

    def test_unrelated_org_role_blocked(self):
        p = _principal("organization:_owner:other-org")
        with pytest.raises(ForbiddenException):
            _check_organization_write_permission(p, "o1")

    def test_admin_bypasses(self):
        admin = _principal(is_admin=True)
        _check_organization_write_permission(admin, "o1")


class TestCourseFamilyScope:
    def test_owner_allowed(self):
        p = _principal("course_family:_owner:f1")
        _check_course_family_write_permission(p, "f1")

    def test_manager_allowed(self):
        p = _principal("course_family:_manager:f1")
        _check_course_family_write_permission(p, "f1")

    def test_developer_blocked(self):
        p = _principal("course_family:_developer:f1")
        with pytest.raises(ForbiddenException):
            _check_course_family_write_permission(p, "f1")

    def test_no_cross_scope_inheritance(self):
        # An organization role must NOT satisfy a course_family check.
        p = _principal("organization:_owner:f1")
        with pytest.raises(ForbiddenException):
            _check_course_family_write_permission(p, "f1")

    def test_admin_bypasses(self):
        admin = _principal(is_admin=True)
        _check_course_family_write_permission(admin, "f1")


# ---------------------------------------------------------------------------
# Dispatch tests: verify create_message_with_author routes to the right helper
# based on which target field is set (and inherits from a parent).
# ---------------------------------------------------------------------------


class TestPrimaryTargetDispatch:
    """For each primary target, exactly one per-scope helper must fire."""

    @pytest.mark.parametrize(
        "field,helper_name,extra_call_args",
        [
            ("organization_id", "_check_organization_write_permission", ("o1",)),
            ("course_family_id", "_check_course_family_write_permission", ("f1",)),
            ("course_id", "_check_course_write_permission", ("c1",)),
            ("course_group_id", "_check_course_group_write_permission", ("g1",)),
            ("course_content_id", "_check_course_content_write_permission", ("cc1",)),
            ("submission_group_id", "_check_submission_group_write_permission", ("sg1",)),
        ],
    )
    def test_dispatch_routes_to_expected_helper(
        self, monkeypatch, field, helper_name, extra_call_args
    ):
        mocks = _stub_helpers(monkeypatch)
        p = _principal(is_admin=True)
        payload = _payload(**{field: extra_call_args[0]})
        create_message_with_author(payload, p, db=MagicMock())

        # The expected helper fired exactly once...
        assert mocks[helper_name].call_count == 1
        # ...and no other scope helper did.
        for other_name, mock in mocks.items():
            if other_name == helper_name:
                continue
            assert mock.call_count == 0, f"{other_name} should not have been called"

    def test_no_targets_dispatches_global(self, monkeypatch):
        mocks = _stub_helpers(monkeypatch)
        p = _principal(is_admin=True)
        create_message_with_author(_payload(), p, db=MagicMock())
        mocks["_check_global_write_permission"].assert_called_once_with(p)

    def test_user_id_target_raises_not_implemented(self, monkeypatch):
        # Even with the helpers stubbed, user_id must dispatch to the
        # "not implemented" guard. We restore the real check (captured
        # at module import time before any stubbing).
        _stub_helpers(monkeypatch)
        monkeypatch.setattr(
            messages_bl,
            "_check_user_message_write_permission",
            _real_user_check,
        )
        p = _principal(is_admin=True)
        with pytest.raises(NotImplementedException):
            create_message_with_author(
                _payload(user_id="u-2"), p, db=MagicMock()
            )

    def test_course_member_id_target_raises_not_implemented(self, monkeypatch):
        _stub_helpers(monkeypatch)
        p = _principal(is_admin=True)
        with pytest.raises(NotImplementedException):
            create_message_with_author(
                _payload(course_member_id="cm-1"), p, db=MagicMock()
            )


class TestPrimaryTargetSelection:
    """When multiple targets are set, the most-specific one wins and the
    rest are nulled out before persistence."""

    def test_submission_group_wins_over_course(self, monkeypatch):
        mocks = _stub_helpers(monkeypatch)
        p = _principal(is_admin=True)
        result = create_message_with_author(
            _payload(submission_group_id="sg1", course_id="c1", organization_id="o1"),
            p,
            db=MagicMock(),
        )
        # submission_group is more specific than course is more specific than org.
        assert result["submission_group_id"] == "sg1"
        assert result["course_id"] is None
        assert result["organization_id"] is None
        mocks["_check_submission_group_write_permission"].assert_called_once()

    def test_course_wins_over_org_and_family(self, monkeypatch):
        mocks = _stub_helpers(monkeypatch)
        p = _principal(is_admin=True)
        result = create_message_with_author(
            _payload(course_id="c1", course_family_id="f1", organization_id="o1"),
            p,
            db=MagicMock(),
        )
        assert result["course_id"] == "c1"
        assert result["course_family_id"] is None
        assert result["organization_id"] is None
        mocks["_check_course_write_permission"].assert_called_once()

    def test_family_wins_over_org(self, monkeypatch):
        mocks = _stub_helpers(monkeypatch)
        p = _principal(is_admin=True)
        result = create_message_with_author(
            _payload(course_family_id="f1", organization_id="o1"),
            p,
            db=MagicMock(),
        )
        assert result["course_family_id"] == "f1"
        assert result["organization_id"] is None
        mocks["_check_course_family_write_permission"].assert_called_once()


# ---------------------------------------------------------------------------
# Reply / parent-inheritance tests
# ---------------------------------------------------------------------------


def _mock_db_returning_message(parent_message):
    """db.query(Message).filter(...).first() returns parent_message."""

    db = MagicMock()
    chain = MagicMock()
    chain.first.return_value = parent_message
    db.query.return_value.filter.return_value = chain
    return db


class TestReplyInheritance:
    def test_reply_inherits_parent_target(self, monkeypatch):
        mocks = _stub_helpers(monkeypatch)
        parent = SimpleNamespace(
            **{f: None for f in MESSAGE_TARGET_FIELDS},
            id="m-parent",
        )
        parent.course_id = "c1"
        db = _mock_db_returning_message(parent)
        p = _principal(is_admin=True)

        result = create_message_with_author(
            _payload(parent_id="m-parent"), p, db
        )

        assert result["course_id"] == "c1"
        # Inherited target dispatches to course helper, not global.
        mocks["_check_course_write_permission"].assert_called_once()
        mocks["_check_global_write_permission"].assert_not_called()

    def test_reply_with_mismatched_target_rejected(self, monkeypatch):
        _stub_helpers(monkeypatch)
        parent = SimpleNamespace(
            **{f: None for f in MESSAGE_TARGET_FIELDS},
            id="m-parent",
        )
        parent.course_id = "c1"
        db = _mock_db_returning_message(parent)
        p = _principal(is_admin=True)

        with pytest.raises(BadRequestException):
            create_message_with_author(
                _payload(parent_id="m-parent", course_id="c-other"),
                p,
                db,
            )

    def test_reply_to_missing_parent_rejected(self):
        db = _mock_db_returning_message(parent_message=None)
        p = _principal(is_admin=True)
        with pytest.raises(BadRequestException):
            create_message_with_author(
                _payload(parent_id="m-missing"), p, db
            )


# ---------------------------------------------------------------------------
# Misc invariants
# ---------------------------------------------------------------------------


class TestInvariants:
    def test_empty_content_rejected(self):
        p = _principal(is_admin=True)
        with pytest.raises(BadRequestException):
            create_message_with_author(_payload(content=""), p, db=MagicMock())

    def test_author_id_always_overridden(self, monkeypatch):
        # The caller cannot spoof author_id — it's always pulled from the
        # principal regardless of payload contents.
        _stub_helpers(monkeypatch)
        p = _principal(is_admin=True, user_id="u-real")
        result = create_message_with_author(
            _payload(course_id="c1", author_id="u-spoofed"),
            p,
            db=MagicMock(),
        )
        assert result["author_id"] == "u-real"

    def test_default_level_zero(self, monkeypatch):
        _stub_helpers(monkeypatch)
        p = _principal(is_admin=True)
        result = create_message_with_author(
            _payload(course_id="c1"), p, db=MagicMock()
        )
        assert result["level"] == 0
