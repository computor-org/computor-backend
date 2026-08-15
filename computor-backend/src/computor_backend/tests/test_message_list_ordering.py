"""``GET /messages`` pagination must be deterministic.

``list_messages_with_filters`` applies limit/offset, and neither the
permission base query nor ``MessageInterface.search`` orders the rows —
so the planner was free to return pages that overlap or skip messages
between requests. The fix pins ``created_at DESC, id DESC`` (newest
first, id as tiebreaker) onto the paginated query.

Compile-style test, like ``test_message_soft_delete_filter``: the order
clause is a property of the SQL the function builds, so we capture the
statement instead of booting a database.
"""
from unittest.mock import MagicMock

from sqlalchemy.orm import Query

import computor_backend.business_logic.messages.core as core
from computor_backend.model.message import Message
from computor_types.messages import MessageQuery


def _paginated_sql(monkeypatch, params: MessageQuery) -> str:
    monkeypatch.setattr(core, "check_permissions", lambda *a, **k: Query([Message]))
    monkeypatch.setattr(Query, "count", lambda self: 0)

    captured = {}

    def _capture_all(self):
        captured["sql"] = str(self.statement.compile())
        return []

    monkeypatch.setattr(Query, "all", _capture_all)
    core.list_messages_with_filters(MagicMock(user_id="u-1"), MagicMock(), params)
    return captured["sql"]


def test_page_query_orders_newest_first(monkeypatch):
    sql = _paginated_sql(monkeypatch, MessageQuery())
    assert "ORDER BY message.created_at DESC, message.id DESC" in sql


def test_order_applies_before_limit(monkeypatch):
    sql = _paginated_sql(monkeypatch, MessageQuery(limit=3))
    order_at = sql.index("ORDER BY message.created_at DESC")
    limit_at = sql.index("LIMIT")
    assert order_at < limit_at


def test_order_survives_filters(monkeypatch):
    sql = _paginated_sql(monkeypatch, MessageQuery(unread=None, scope="course"))
    assert "ORDER BY message.created_at DESC, message.id DESC" in sql
