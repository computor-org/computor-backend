"""Unit tests for message-driven cache invalidation.

Three concerns:

1. ``invalidate_dashboard_views_for_message`` — every message scope
   resolves to the right set of affected courses, and each one busts
   ``tutor_view`` / ``lecturer_view`` / ``student_view`` tags. Replaces
   the older ``invalidate_tutor_lecturer_views_for_message`` which only
   knew about ``submission_group`` and ``course_content`` scopes.

2. ``_invalidate_message_cache`` — read-state changes additionally bust
   the message's entity tag (``submission_group:<id>``, etc.) so any
   downstream cached view keyed on that scope picks up the new state.
   This now covers org / course_family too (used to silently miss).

3. ``post_create_course_member`` / ``post_update_course_member`` — bust
   the course's dashboard caches so a freshly added member or a role
   change is visible immediately, not after TTL.

We mock the cache + DB. Real SQL behaviour is verified against the dev
DB out-of-band; here we only check the dispatch and that the right
tags are passed to ``cache.invalidate_tags``.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from computor_backend.business_logic import messages as messages_bl


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _msg(**targets):
    """Fake Message-shaped object — same helper as the WS-broadcast tests."""
    base = dict(
        id="m-1",
        author_id="u-author",
        user_id=None,
        course_member_id=None,
        submission_group_id=None,
        course_content_id=None,
        course_group_id=None,
        course_id=None,
        course_family_id=None,
        organization_id=None,
    )
    base.update(targets)
    return SimpleNamespace(**base)


def _cache():
    """Cache mock that records every invalidate_tags call."""
    c = MagicMock()
    c.invalidated = []
    c.invalidate_tags.side_effect = lambda *tags: c.invalidated.extend(tags)
    c.invalidate_user_views = MagicMock()
    return c


def _patch_course_resolution(monkeypatch, course_ids):
    """Stub ``_affected_course_ids_for_message`` so we don't need a real DB
    schema to drive the invalidator's branching logic."""
    monkeypatch.setattr(
        messages_bl,
        "_affected_course_ids_for_message",
        lambda message, db: set(course_ids),
    )


# ---------------------------------------------------------------------------
# invalidate_dashboard_views_for_message
# ---------------------------------------------------------------------------


class TestDashboardViewInvalidation:
    def test_no_op_when_cache_is_none(self, monkeypatch):
        # Defensive: every test environment without Redis attached must
        # still work; the helper simply skips invalidation.
        _patch_course_resolution(monkeypatch, ["c-1"])
        messages_bl.invalidate_dashboard_views_for_message(
            _msg(course_id="c-1"), db=MagicMock(), cache=None
        )  # no raise

    def test_no_op_when_message_is_none(self):
        # Same defensive contract for None messages.
        cache = _cache()
        messages_bl.invalidate_dashboard_views_for_message(
            None, db=MagicMock(), cache=cache
        )
        assert cache.invalidated == []

    @pytest.mark.parametrize(
        "field,target_id",
        [
            ("course_id", "c-1"),
            ("submission_group_id", "sg-1"),
            ("course_content_id", "cc-1"),
            ("course_group_id", "cg-1"),
            ("course_member_id", "cm-1"),
        ],
    )
    def test_single_course_scopes_bust_three_tags(self, monkeypatch, field, target_id):
        # Each per-course scope resolves to exactly one course and
        # busts its three dashboard view tags.
        _patch_course_resolution(monkeypatch, ["c-1"])
        cache = _cache()
        messages_bl.invalidate_dashboard_views_for_message(
            _msg(**{field: target_id}), db=MagicMock(), cache=cache
        )
        assert set(cache.invalidated) == {
            "tutor_view:c-1",
            "lecturer_view:c-1",
            "student_view:c-1",
        }

    def test_course_family_scope_busts_every_course_in_family(self, monkeypatch):
        # Family-scoped messages cascade — every course inside the
        # family needs its dashboards refreshed.
        _patch_course_resolution(monkeypatch, ["c-1", "c-2", "c-3"])
        cache = _cache()
        messages_bl.invalidate_dashboard_views_for_message(
            _msg(course_family_id="f-1"), db=MagicMock(), cache=cache
        )
        # 3 courses × 3 view tags = 9 invalidations.
        assert len(cache.invalidated) == 9
        for cid in ("c-1", "c-2", "c-3"):
            assert f"tutor_view:{cid}" in cache.invalidated
            assert f"lecturer_view:{cid}" in cache.invalidated
            assert f"student_view:{cid}" in cache.invalidated

    def test_organization_scope_busts_every_course_in_org(self, monkeypatch):
        # Symmetric to course_family — same cascade pattern.
        _patch_course_resolution(monkeypatch, ["c-1", "c-2"])
        cache = _cache()
        messages_bl.invalidate_dashboard_views_for_message(
            _msg(organization_id="o-1"), db=MagicMock(), cache=cache
        )
        assert len(cache.invalidated) == 6

    def test_global_message_does_not_touch_dashboards(self, monkeypatch):
        # Global posts surface in the inbox sidebar (via the user:<id>
        # WS channel), not in per-course unread badges. No invalidation.
        _patch_course_resolution(monkeypatch, [])
        cache = _cache()
        messages_bl.invalidate_dashboard_views_for_message(
            _msg(), db=MagicMock(), cache=cache
        )
        assert cache.invalidated == []

    def test_user_id_message_does_not_touch_dashboards(self, monkeypatch):
        # Direct chat doesn't surface in any course dashboard.
        _patch_course_resolution(monkeypatch, [])
        cache = _cache()
        messages_bl.invalidate_dashboard_views_for_message(
            _msg(user_id="u-1"), db=MagicMock(), cache=cache
        )
        assert cache.invalidated == []

    def test_back_compat_alias_still_resolves(self):
        # External integration scripts (tests/seed/verify_message_*.py)
        # import the old name. Removing the alias would break them.
        assert (
            messages_bl.invalidate_tutor_lecturer_views_for_message
            is messages_bl.invalidate_dashboard_views_for_message
        )


# ---------------------------------------------------------------------------
# _invalidate_message_cache (read/unread state-change invalidation)
# ---------------------------------------------------------------------------


def _patch_db_returning_message(monkeypatch, message):
    """Stub ``db.query(Message).filter(...).first()`` to return ``message``."""

    db = MagicMock()
    chain = MagicMock()
    chain.first.return_value = message
    db.query.return_value.filter.return_value = chain
    return db


class TestReadInvalidationEntityTags:
    """The read-state invalidator now covers org and course_family targets;
    they used to silently fall through with no entity-tag invalidation."""

    def test_organization_scope_busts_org_entity_tags(self):
        cache = _cache()
        msg = _msg(organization_id="o-1")
        db = _patch_db_returning_message(None, msg)
        messages_bl._invalidate_message_cache("m-1", "u-reader", db, cache)
        assert "organization:o-1" in cache.invalidated
        assert "organization_id:o-1" in cache.invalidated
        cache.invalidate_user_views.assert_called_once()

    def test_course_family_scope_busts_family_entity_tags(self):
        cache = _cache()
        msg = _msg(course_family_id="f-1")
        db = _patch_db_returning_message(None, msg)
        messages_bl._invalidate_message_cache("m-1", "u-reader", db, cache)
        assert "course_family:f-1" in cache.invalidated
        assert "course_family_id:f-1" in cache.invalidated

    def test_existing_scopes_still_invalidate(self):
        # Regression: the org/family additions must not have broken the
        # existing per-scope branches.
        cache = _cache()
        msg = _msg(submission_group_id="sg-1")
        db = _patch_db_returning_message(None, msg)
        messages_bl._invalidate_message_cache("m-1", "u-reader", db, cache)
        assert "submission_group:sg-1" in cache.invalidated

    def test_missing_message_is_noop(self):
        # Defensive: if the row vanished between the trigger and the
        # invalidation lookup, just skip.
        cache = _cache()
        db = _patch_db_returning_message(None, None)
        messages_bl._invalidate_message_cache("m-missing", "u-1", db, cache)
        assert cache.invalidated == []


# ---------------------------------------------------------------------------
# invalidate_course_dashboards (the helper shared by message + member paths)
# ---------------------------------------------------------------------------


class TestCourseDashboardInvalidation:
    def test_busts_three_view_tags(self):
        cache = _cache()
        messages_bl.invalidate_course_dashboards("c-1", cache)
        assert set(cache.invalidated) == {
            "tutor_view:c-1",
            "lecturer_view:c-1",
            "student_view:c-1",
        }

    def test_no_op_without_cache(self):
        # Hooks are wired with get_cache() which can return None during
        # cold start / test contexts; helper must tolerate it.
        messages_bl.invalidate_course_dashboards("c-1", None)  # no raise

    def test_no_op_without_course_id(self):
        # Defensive — a freshly inserted CourseMember might briefly
        # have course_id unset in pathological cases; don't crash.
        cache = _cache()
        messages_bl.invalidate_course_dashboards(None, cache)
        assert cache.invalidated == []

    def test_uuid_input_coerced_to_string(self):
        # The CourseMember model gives us a UUID, but tags are strings.
        from uuid import UUID

        cache = _cache()
        cid = UUID("12345678-1234-5678-1234-567812345678")
        messages_bl.invalidate_course_dashboards(cid, cache)
        assert f"tutor_view:{cid}" in cache.invalidated
