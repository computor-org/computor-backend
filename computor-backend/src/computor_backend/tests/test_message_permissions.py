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

from computor_backend.exceptions import (
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
        # Use a conversational scope (submission_group) so the
        # non-conversational reply guard doesn't fire — this test is
        # specifically about target inheritance, not the reply policy.
        mocks = _stub_helpers(monkeypatch)
        parent = SimpleNamespace(
            **{f: None for f in MESSAGE_TARGET_FIELDS},
            id="m-parent",
        )
        parent.submission_group_id = "sg1"
        db = _mock_db_returning_message(parent)
        p = _principal(is_admin=True)

        result = create_message_with_author(
            _payload(parent_id="m-parent"), p, db
        )

        assert result["submission_group_id"] == "sg1"
        # Inherited target dispatches to the submission_group helper, not global.
        mocks["_check_submission_group_write_permission"].assert_called_once()
        mocks["_check_global_write_permission"].assert_not_called()

    def test_reply_with_mismatched_target_rejected(self, monkeypatch):
        _stub_helpers(monkeypatch)
        parent = SimpleNamespace(
            **{f: None for f in MESSAGE_TARGET_FIELDS},
            id="m-parent",
        )
        parent.submission_group_id = "sg1"
        db = _mock_db_returning_message(parent)
        p = _principal(is_admin=True)

        with pytest.raises(BadRequestException):
            create_message_with_author(
                _payload(parent_id="m-parent", submission_group_id="sg-other"),
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


class TestNonConversationalReplyGuard:
    """``parent_id`` replies are only meaningful on conversational scopes
    (user / course_member / submission_group). Replying on broadcast
    scopes (global / org / family / course / course_group / course_content)
    would fan out a student's reply to the announcement audience — the
    opposite of what an announcement is for. Server-side enforcement
    mirrors the client-side reply policy.
    """

    def _mock_db_with_parent(self, parent_target_field, parent_target_id="t-1"):
        """Build a mock db whose Message-by-id query returns a parent
        with the given target column populated."""
        parent = SimpleNamespace(
            **{f: None for f in [
                "user_id", "course_member_id", "submission_group_id",
                "course_content_id", "course_group_id", "course_id",
                "course_family_id", "organization_id",
            ]},
            id="m-parent",
        )
        if parent_target_field is not None:
            setattr(parent, parent_target_field, parent_target_id)
        db = MagicMock()
        chain = MagicMock()
        chain.first.return_value = parent
        db.query.return_value.filter.return_value = chain
        return db

    @pytest.mark.parametrize("parent_target", [
        "organization_id",
        "course_family_id",
        "course_id",
        "course_group_id",
        "course_content_id",
    ])
    def test_reply_to_announcement_scope_rejected(self, monkeypatch, parent_target):
        # Replies inherit the parent's target during create_message_with_author;
        # by the time the guard runs the resolved primary_target == parent_target.
        _stub_helpers(monkeypatch)
        db = self._mock_db_with_parent(parent_target)
        admin = _principal(is_admin=True)
        with pytest.raises(BadRequestException) as exc:
            create_message_with_author(_payload(parent_id="m-parent"), admin, db)
        assert "announcement-only" in str(exc.value.detail).lower() or \
               "not allowed" in str(exc.value.detail).lower()

    def test_reply_to_global_message_rejected(self, monkeypatch):
        # A parent with NO target columns set is the global scope — same
        # rule applies; non-conversational.
        _stub_helpers(monkeypatch)
        db = self._mock_db_with_parent(parent_target_field=None)
        admin = _principal(is_admin=True)
        with pytest.raises(BadRequestException):
            create_message_with_author(_payload(parent_id="m-parent"), admin, db)

    @pytest.mark.parametrize("parent_target", [
        "user_id",
        "course_member_id",
        "submission_group_id",
    ])
    def test_reply_to_conversational_scope_does_not_fire_guard(
        self, monkeypatch, parent_target
    ):
        # The three conversational scopes accept replies. The reply
        # guard must not raise BadRequestException for them — what
        # happens downstream (NotImplementedException for user_id /
        # course_member_id, dispatch to the real helper for
        # submission_group) is a separate concern.
        _stub_helpers(monkeypatch)
        db = self._mock_db_with_parent(parent_target)
        admin = _principal(is_admin=True)
        try:
            create_message_with_author(_payload(parent_id="m-parent"), admin, db)
        except BadRequestException as exc:
            # The only acceptable BadRequest from this path would NOT
            # mention the announcement-only / reply rule.
            assert "announcement-only" not in str(exc.detail).lower()
            assert "not allowed" not in str(exc.detail).lower()
        except NotImplementedException:
            # Expected for the user_id / course_member_id branches.
            pass


class TestAuthorAutoRead:
    """``mark_author_as_reader`` is the create-path shortcut that
    eliminates the ``always-1-unread`` UX artefact for authors. It must
    insert a MessageRead row keyed on the message and the author user,
    and it must swallow IntegrityError on duplicate insert (idempotent
    for races with a concurrent manual mark-read).
    """

    def test_inserts_message_read_row(self):
        from computor_backend.business_logic import messages as messages_bl

        db = MagicMock()
        messages_bl.mark_author_as_reader("m-1", "u-author", db)

        # MessageRead model was instantiated and added.
        added = db.add.call_args[0][0]
        assert added.message_id == "m-1"
        assert added.reader_user_id == "u-author"
        db.commit.assert_called_once()

    def test_swallows_integrity_error_on_duplicate(self):
        # If the author somehow already has a MessageRead row for the
        # message (race condition with a manual mark-read), the create
        # endpoint must NOT fail. The duplicate is silently ignored.
        from sqlalchemy.exc import IntegrityError

        from computor_backend.business_logic import messages as messages_bl

        db = MagicMock()
        db.commit.side_effect = IntegrityError("duplicate", {}, Exception())

        # Should not raise — the create endpoint depends on this.
        messages_bl.mark_author_as_reader("m-1", "u-author", db)
        db.rollback.assert_called_once()


class TestAdminBypass:
    """Admin must be able to post to every targeted scope without holding
    a course / scoped role. Scope rules apply only to non-admin users.

    Regression guard: the DB-based write helpers (course / course_group /
    course_content / submission_group) used to call straight into a
    CourseMember query that returned False for admins (admins have no
    course memberships) and 403'd them. We now short-circuit on
    ``is_admin`` before the DB hits.
    """

    @pytest.mark.parametrize(
        "field,target_id",
        [
            ("course_id", "c-1"),
            ("course_content_id", "cc-1"),
            ("course_group_id", "cg-1"),
            ("submission_group_id", "sg-1"),
        ],
    )
    def test_admin_bypasses_db_based_write_checks(self, field, target_id):
        admin = _principal(is_admin=True)
        # No DB stubbing — the helper must short-circuit BEFORE issuing
        # any query, so a bare MagicMock() session is fine.
        result = create_message_with_author(
            _payload(**{field: target_id}), admin, db=MagicMock()
        )
        assert result[field] == target_id


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
