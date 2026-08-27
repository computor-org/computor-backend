"""``parent_author_id`` enrichment: replies carry their parent's author.

The WS ``message:new`` broadcast is the enriched ``MessageGet`` dump, so a
client can only decide "is this a reply to me?" if the parent's author rides
along. These tests pin the batched resolver (no queries for root-only pages,
one query per page otherwise) and the DTO shape the broadcast depends on.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from computor_backend.business_logic.messages.read_status import _get_parent_author_ids
from computor_types.messages import MessageGet


def _msg(i, parent_id=None, author_id="u-1"):
    return SimpleNamespace(id=f"m-{i}", parent_id=parent_id, author_id=author_id)


class _CountingDB:
    def __init__(self, rows):
        self.queries = 0
        self._rows = rows

    def query(self, *cols):
        self.queries += 1
        q = MagicMock()
        q.filter.return_value.all.return_value = self._rows
        return q


def test_roots_need_no_query_and_map_to_none():
    msgs = [_msg(i) for i in range(50)]
    db = _CountingDB([])
    out = _get_parent_author_ids(msgs, db)
    assert db.queries == 0
    assert set(out.values()) == {None}
    assert len(out) == 50


def test_replies_map_to_their_parents_author():
    msgs = [_msg(0), _msg(1, parent_id="m-0"), _msg(2, parent_id="p-x")]
    db = _CountingDB([("m-0", "u-root"), ("p-x", "u-other")])
    out = _get_parent_author_ids(msgs, db)
    assert out["m-0"] is None
    assert out["m-1"] == "u-root"
    assert out["m-2"] == "u-other"


def test_query_count_is_flat_in_page_size():
    for n in (1, 10, 500):
        msgs = [_msg(i, parent_id=f"p-{i % 7}") for i in range(n)]
        db = _CountingDB([(f"p-{k}", f"u-{k}") for k in range(7)])
        out = _get_parent_author_ids(msgs, db)
        assert db.queries == 1, f"n={n} issued {db.queries} queries"
        assert out["m-0"] == "u-0"


def test_missing_parent_resolves_to_none():
    msgs = [_msg(0, parent_id="gone")]
    db = _CountingDB([])
    out = _get_parent_author_ids(msgs, db)
    assert out["m-0"] is None


def test_message_get_dump_carries_parent_author_id():
    # The broadcast payload is model_dump() minus is_read/is_author, so the
    # field must exist on the DTO and default to None for roots.
    dump = MessageGet(id="m-1", content="hi", level=0, author_id="u-1").model_dump()
    assert "parent_author_id" in dump
    assert dump["parent_author_id"] is None

    reply = MessageGet(
        id="m-2", content="re", level=1, author_id="u-2",
        parent_id="m-1", parent_author_id="u-1",
    ).model_dump()
    assert reply["parent_author_id"] == "u-1"
