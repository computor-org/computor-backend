"""Query counts for message list enrichment must not scale with page size.

``list_messages_with_read_status`` runs the author, read-status and mention
enrichers over every row the list endpoint returns. Both the author enricher
and the mention enricher need to know each message's course, which is either
stamped on the row or reachable through its target.

Resolving that per message costs a lazy-load SELECT each, plus (in the author
enricher) a CourseMember query each. The extension auto-pages at 500 rows, so
a single panel open could issue thousands of queries. These tests pin the
batched resolver at a fixed query count regardless of how many messages are
in the page.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from computor_backend.business_logic.messages.audience import course_ids_for_messages
from computor_types.messages import MESSAGE_TARGET_FIELDS


def _msg(i, **targets):
    base = {f: None for f in MESSAGE_TARGET_FIELDS}
    base.update(targets)
    return SimpleNamespace(id=f"m-{i}", author_id="u-1", **base)


class _CountingDB:
    def __init__(self, rows):
        self.queries = 0
        self._rows = rows

    def query(self, *cols):
        self.queries += 1
        q = MagicMock()
        q.filter.return_value.all.return_value = self._rows
        return q


def test_query_count_is_flat_in_batch_size():
    for n in (1, 10, 500):
        msgs = [_msg(i, submission_group_id="sg-1") for i in range(n)]
        db = _CountingDB([("sg-1", "c-1")])
        out = course_ids_for_messages(msgs, db)
        assert db.queries == 1, f"n={n} issued {db.queries} queries"
        assert out["m-0"] == "c-1"


def test_one_query_per_distinct_target_type_not_per_message():
    msgs = (
        [_msg(i, submission_group_id="sg-1") for i in range(100)]
        + [_msg(100 + i, course_content_id="cc-1") for i in range(100)]
        + [_msg(200 + i, course_group_id="cg-1") for i in range(100)]
        + [_msg(300 + i, course_member_id="cm-1") for i in range(100)]
    )
    db = _CountingDB([("x", "c-1")])
    course_ids_for_messages(msgs, db)
    assert db.queries == 4


def test_direct_course_id_needs_no_query_at_all():
    msgs = [_msg(i, course_id="c-1") for i in range(50)]
    db = _CountingDB([])
    out = course_ids_for_messages(msgs, db)
    assert db.queries == 0
    assert out["m-0"] == "c-1"


def test_scopes_without_a_course_resolve_to_none():
    msgs = [_msg(0), _msg(1, organization_id="o-1"), _msg(2, course_family_id="f-1"),
            _msg(3, user_id="u-2")]
    db = _CountingDB([])
    out = course_ids_for_messages(msgs, db)
    assert db.queries == 0
    assert set(out.values()) == {None}
