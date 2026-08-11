"""A deleted message survives in a thread only while replies hang off it.

``soft_delete_message`` keeps the row and rewrites its body to a tombstone
("[This message was deleted by ...]") precisely so replies stay attached.
Every read path then filtered ``archived_at IS NULL`` unconditionally, which
removed the node but not its children — so replies came back pointing at a
parent that wasn't in the response, and the tombstone was never displayed
anywhere.

``get_message_thread`` now keeps a deleted message when it still has a live
descendant, and drops it when it doesn't. These tests drive the retention
rule directly with a stubbed DB; the SQL-level filter for the *list*
endpoint is covered in test_message_soft_delete_filter.py.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from computor_backend.business_logic.messages import core as messages_core
from computor_types.messages import MESSAGE_TARGET_FIELDS

ARCHIVED = datetime(2026, 8, 1, tzinfo=timezone.utc)


def _m(mid, parent_id=None, archived=False, created=1):
    return SimpleNamespace(
        id=mid,
        parent_id=parent_id,
        archived_at=ARCHIVED if archived else None,
        created_at=datetime(2026, 8, 1, 12, created, tzinfo=timezone.utc),
        author_id="u-1",
        title=None,
        content="hi",
        level=0,
        **{f: None for f in MESSAGE_TARGET_FIELDS},
    )


def _thread(monkeypatch, messages, anchor_id):
    """Run get_message_thread over a fixed set of thread messages."""
    by_id = {m.id: m for m in messages}

    db = MagicMock()

    # get_message_thread issues four queries in a fixed order: the anchor
    # lookup, the recursive CTE's two halves, then the thread fetch.
    anchor_query = MagicMock()
    anchor_query.filter.return_value.first.return_value = by_id[anchor_id]

    cte_obj = MagicMock()
    cte_obj.union_all.return_value = cte_obj
    id_query = MagicMock()
    id_query.filter.return_value.cte.return_value = cte_obj
    id_query.filter.return_value.all.return_value = []

    fetch_query = MagicMock()
    fetch_query.filter.return_value.order_by.return_value.all.return_value = list(messages)

    calls = {"n": 0}

    def query_side_effect(*args):
        calls["n"] += 1
        if calls["n"] == 1:
            return anchor_query
        if calls["n"] in (2, 3):
            return id_query
        return fetch_query

    db.query.side_effect = query_side_effect

    monkeypatch.setattr(
        messages_core, "list_messages_with_read_status", lambda items, p, d: items
    )
    return messages_core.get_message_thread(anchor_id, MagicMock(), db)


def test_deleted_message_with_a_live_reply_is_kept(monkeypatch):
    messages = [_m("root", created=1), _m("mid", "root", archived=True, created=2),
                _m("leaf", "mid", created=3)]
    result = _thread(monkeypatch, messages, "root")
    ids = [m.id for m in result.messages]
    # The tombstone stays so the leaf keeps its context.
    assert ids == ["root", "mid", "leaf"]


def test_deleted_leaf_is_dropped(monkeypatch):
    messages = [_m("root", created=1), _m("gone", "root", archived=True, created=2)]
    result = _thread(monkeypatch, messages, "root")
    assert [m.id for m in result.messages] == ["root"]


def test_deleted_chain_is_kept_all_the_way_down_to_a_live_reply(monkeypatch):
    messages = [
        _m("root", created=1),
        _m("d1", "root", archived=True, created=2),
        _m("d2", "d1", archived=True, created=3),
        _m("leaf", "d2", created=4),
    ]
    result = _thread(monkeypatch, messages, "root")
    assert [m.id for m in result.messages] == ["root", "d1", "d2", "leaf"]


def test_deleted_subtree_with_no_live_reply_is_dropped_entirely(monkeypatch):
    messages = [
        _m("root", created=1),
        _m("d1", "root", archived=True, created=2),
        _m("d2", "d1", archived=True, created=3),
    ]
    result = _thread(monkeypatch, messages, "root")
    assert [m.id for m in result.messages] == ["root"]


def test_anchor_may_itself_be_deleted(monkeypatch):
    # GET /messages/{id} resolves a deleted message, so refusing here made
    # the two endpoints disagree.
    messages = [_m("gone", archived=True, created=1), _m("leaf", "gone", created=2)]
    result = _thread(monkeypatch, messages, "gone")
    assert [m.id for m in result.messages] == ["gone", "leaf"]


def test_missing_anchor_still_raises(monkeypatch):
    from computor_backend.exceptions import BadRequestException

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(BadRequestException):
        messages_core.get_message_thread("nope", MagicMock(), db)
