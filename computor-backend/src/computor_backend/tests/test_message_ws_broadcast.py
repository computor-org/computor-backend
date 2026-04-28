"""Unit tests for the WebSocket broadcast surface for messages.

Covers three concerns:

1. **Channel enumeration** — given a message row, ``_get_message_channels``
   returns the right scope channel and ``_get_all_channels`` adds the
   per-recipient inbox channels (or falls back to ``GLOBAL_CHANNEL`` for
   global messages).

2. **read_updated** — the refactored signature publishes to every scope
   channel of the message PLUS the reader's own ``user:<id>`` channel,
   carrying ``read=True/False`` so unread can be distinguished on the wire.

3. **Audience helper dispatch** — ``get_message_recipient_user_ids``
   routes to the correct per-scope SQL branch and always includes the
   author plus every system admin.

The audience helper does ~10 DB queries per call across multiple models;
verifying every SQL line in unit tests would require a full schema. We
stub the per-branch query dispatch with mocks here and rely on the dev
DB smoke tests for end-to-end verification (see the conversation history
for the actual SQL traces).
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computor_backend.business_logic import messages as messages_bl
from computor_backend.websocket import broadcast as broadcast_mod
from computor_backend.websocket.broadcast import (
    GLOBAL_CHANNEL,
    WebSocketBroadcast,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _msg(**targets):
    """Build a fake Message-shaped object.

    All target columns default to None; pass kwargs to set specific ones.
    Author defaults to a stable id so the audience always has at least one
    member when a real audience computation runs.
    """
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


def _run(coro):
    """Run a coroutine to completion in a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Channel enumeration — _get_message_channels
# ---------------------------------------------------------------------------


class TestScopeChannelEnumeration:
    def setup_method(self):
        self.b = WebSocketBroadcast()

    @pytest.mark.parametrize(
        "field,channel_prefix",
        [
            ("organization_id", "organization"),
            ("course_family_id", "course_family"),
            ("course_id", "course"),
            ("course_group_id", "course_group"),
            ("course_content_id", "course_content"),
            ("submission_group_id", "submission_group"),
        ],
    )
    def test_single_target_returns_single_scope_channel(self, field, channel_prefix):
        m = _msg(**{field: "x-1"})
        assert self.b._get_message_channels(m) == [f"{channel_prefix}:x-1"]

    def test_no_target_returns_empty(self):
        # Global messages have no scope channel — caller falls back to
        # GLOBAL_CHANNEL via _get_all_channels.
        assert self.b._get_message_channels(_msg()) == []

    def test_dedupes_defensively_for_legacy_multi_target_rows(self):
        # Single-target invariant is enforced at create, but the channel
        # helper must stay correct if a legacy row has more than one
        # column set. Order is most-specific first.
        m = _msg(submission_group_id="sg-1", course_id="c-1")
        assert self.b._get_message_channels(m) == [
            "submission_group:sg-1",
            "course:c-1",
        ]


# ---------------------------------------------------------------------------
# Channel enumeration — _get_all_channels (scope + inbox + global fallback)
# ---------------------------------------------------------------------------


class TestAllChannelsEnumeration:
    def setup_method(self):
        self.b = WebSocketBroadcast()

    def test_global_message_returns_only_global_channel(self):
        # No DB lookup, no per-user fanout — every connection is auto-
        # subscribed to the global channel so a single publish reaches
        # everyone.
        channels = self.b._get_all_channels(_msg(), db=MagicMock())
        assert channels == [GLOBAL_CHANNEL]

    def test_targeted_message_combines_scope_and_inbox(self, monkeypatch):
        m = _msg(course_id="c-1")
        recipients = {"u-author", "u-admin", "u-student"}
        monkeypatch.setattr(
            messages_bl,
            "get_message_recipient_user_ids",
            lambda message, db: recipients,
        )

        channels = self.b._get_all_channels(m, db=MagicMock())

        # Scope channel comes first (UI subscribes here per-view); inbox
        # channels follow in deterministic sorted order.
        assert channels[0] == "course:c-1"
        assert set(channels[1:]) == {f"user:{uid}" for uid in recipients}
        # Sorted order on the inbox tail makes the output snapshot-stable.
        assert channels[1:] == sorted(channels[1:])

    def test_targeted_with_no_recipients_still_returns_scope_channel(self, monkeypatch):
        # Defensive: a message with a target but somehow zero recipients
        # (e.g. the audience helper returns empty) still publishes to
        # the scope channel — no client crashes from empty broadcasts.
        monkeypatch.setattr(
            messages_bl,
            "get_message_recipient_user_ids",
            lambda message, db: set(),
        )
        channels = self.b._get_all_channels(_msg(course_id="c-1"), db=MagicMock())
        assert channels == ["course:c-1"]


# ---------------------------------------------------------------------------
# read_updated — fan to scope channels + reader's own user channel
# ---------------------------------------------------------------------------


class TestReadUpdated:
    def setup_method(self):
        self.b = WebSocketBroadcast()

    def _capture_publishes(self, monkeypatch):
        """Patch the redis publish path; return a list that will collect
        every (channel, payload_dict) pair the broadcaster sent."""
        captured = []

        async def fake_publish(channel, payload_str):
            captured.append((channel, json.loads(payload_str)))

        fake_redis = SimpleNamespace(publish=fake_publish)

        async def fake_get_redis_client():
            return fake_redis

        monkeypatch.setattr(
            "computor_backend.redis_cache.get_redis_client",
            fake_get_redis_client,
        )
        return captured

    def test_targeted_message_fans_to_scope_and_user_channels(self, monkeypatch):
        captured = self._capture_publishes(monkeypatch)

        _run(self.b.read_updated(
            _msg(course_group_id="cg-1"),
            message_id="m-1",
            user_id="u-reader",
            is_read=True,
        ))

        from computor_backend.websocket.pubsub import CHANNEL_PREFIX
        # Two publishes: scope channel + reader's own inbox.
        assert len(captured) == 2
        channels = [c for c, _ in captured]
        assert f"{CHANNEL_PREFIX}course_group:cg-1" in channels
        assert f"{CHANNEL_PREFIX}user:u-reader" in channels

    def test_payload_carries_read_flag_and_flat_shape(self, monkeypatch):
        captured = self._capture_publishes(monkeypatch)

        _run(self.b.read_updated(
            _msg(course_id="c-1"),
            message_id="m-1",
            user_id="u-reader",
            is_read=False,
        ))

        for channel, payload in captured:
            assert payload["type"] == "read:update"
            assert payload["message_id"] == "m-1"
            assert payload["user_id"] == "u-reader"
            assert payload["read"] is False
            # Flat shape — no nested "data" key (frontend handler relies
            # on this).
            assert "data" not in payload

    def test_global_message_fires_on_global_channel(self, monkeypatch):
        captured = self._capture_publishes(monkeypatch)

        _run(self.b.read_updated(
            _msg(),  # global
            message_id="m-1",
            user_id="u-reader",
            is_read=True,
        ))

        from computor_backend.websocket.pubsub import CHANNEL_PREFIX
        channels = [c for c, _ in captured]
        assert f"{CHANNEL_PREFIX}{GLOBAL_CHANNEL}" in channels
        assert f"{CHANNEL_PREFIX}user:u-reader" in channels


# ---------------------------------------------------------------------------
# Audience helper — get_message_recipient_user_ids
#
# We mock the DB session to verify dispatch (which branch fires per scope)
# and the always-included rules (author + admins). End-to-end SQL is
# verified against the dev DB out-of-band.
# ---------------------------------------------------------------------------


class TestAudienceDispatch:
    def _mock_db_with_admins(self, admin_ids=None, branch_results=None):
        """Build a mock Session.

        - The first ``db.query(UserRole.user_id).filter(...).all()`` returns
          the configured admin id rows.
        - All subsequent ``.filter().first()`` / ``.filter().all()`` chains
          return whatever the test sets on ``branch_results`` (a list,
          consumed in order, of the values to return).
        """
        admin_ids = admin_ids or []
        branch_results = list(branch_results or [])

        admin_rows = [(uid,) for uid in admin_ids]

        # We capture every db.query() call and return a chainable mock
        # whose .filter().all() / .filter().first() / .join() returns the
        # next item in branch_results (or admin_rows for the very first
        # query, which is always the admin lookup).
        admin_yielded = [False]

        def make_chain():
            chain = MagicMock()

            def all_():
                if not admin_yielded[0]:
                    admin_yielded[0] = True
                    return admin_rows
                if branch_results:
                    return branch_results.pop(0)
                return []

            def first_():
                if branch_results:
                    return branch_results.pop(0)
                return None

            chain.filter.return_value = chain
            chain.join.return_value = chain
            chain.all.side_effect = all_
            chain.first.side_effect = first_
            return chain

        db = MagicMock()
        db.query.side_effect = lambda *a, **kw: make_chain()
        return db

    def test_global_message_returns_empty_set(self):
        db = self._mock_db_with_admins(admin_ids=["u-admin"])
        result = messages_bl.get_message_recipient_user_ids(_msg(), db)
        # Global messages skip per-user fanout entirely — broadcast layer
        # publishes to the dedicated global channel instead.
        assert result == set()

    def test_author_always_included(self):
        # Pick a scope where the branch result is empty so we can isolate
        # the author/admin always-included behaviour.
        db = self._mock_db_with_admins(
            admin_ids=[],
            branch_results=[[]],  # empty member rows
        )
        m = _msg(course_id="c-1")
        result = messages_bl.get_message_recipient_user_ids(m, db)
        assert "u-author" in result

    def test_admins_always_included(self):
        db = self._mock_db_with_admins(
            admin_ids=["u-admin-1", "u-admin-2"],
            branch_results=[[]],
        )
        m = _msg(course_id="c-1")
        result = messages_bl.get_message_recipient_user_ids(m, db)
        assert {"u-admin-1", "u-admin-2"}.issubset(result)

    def test_user_id_target_includes_recipient(self):
        db = self._mock_db_with_admins(admin_ids=[])
        m = _msg(user_id="u-recipient")
        result = messages_bl.get_message_recipient_user_ids(m, db)
        assert result == {"u-author", "u-recipient"}

    def test_course_id_target_collects_course_members(self):
        db = self._mock_db_with_admins(
            admin_ids=[],
            branch_results=[
                [("u-1",), ("u-2",), ("u-3",)],  # course_member rows
            ],
        )
        m = _msg(course_id="c-1")
        result = messages_bl.get_message_recipient_user_ids(m, db)
        assert {"u-1", "u-2", "u-3", "u-author"}.issubset(result)
