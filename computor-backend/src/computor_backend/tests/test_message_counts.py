"""``GET /messages/counts`` — aggregate shape, SQL properties, route order.

The endpoint's guarantees:

* visibility comes from the same permission filter as ``GET /messages``
  (``check_permissions`` builds the base query — verified by capturing
  what ``message_counts`` actually executes on top of it);
* soft-deleted rows are excluded;
* ``unread`` never counts the caller's own posts;
* the course is *resolved* (coalesced through the target tables), not
  just the raw ``message.course_id`` column;
* the literal ``/counts`` path is declared before ``/{id}`` so the id
  route cannot swallow it.
"""
from unittest.mock import MagicMock

from sqlalchemy.orm import Query

import computor_backend.business_logic.messages.counts as counts_mod
from computor_backend.model.message import Message
from computor_types.messages import MessageCountsGet


def _run(monkeypatch, rows, base=None):
    """Run message_counts over preset result rows, capturing the SQL."""
    monkeypatch.setattr(
        counts_mod, "check_permissions",
        lambda *a, **k: base if base is not None else Query([Message]),
    )
    captured = {}

    def _capture_all(self):
        captured["sql"] = str(self.statement.compile())
        return rows

    monkeypatch.setattr(Query, "all", _capture_all)
    result = counts_mod.message_counts(MagicMock(user_id="u-1", is_admin=False), MagicMock())
    return result, captured.get("sql", "")


def test_rows_become_sorted_cells_with_totals(monkeypatch):
    result, _ = _run(monkeypatch, [
        ("submission_group", "c-1", 5, 2),
        ("global", None, 3, 1),
        ("course", "c-1", 4, 0),
    ])
    assert isinstance(result, MessageCountsGet)
    assert [(c.scope, c.course_id, c.total, c.unread) for c in result.counts] == [
        ("course", "c-1", 4, 0),
        ("global", None, 3, 1),
        ("submission_group", "c-1", 5, 2),
    ]
    assert result.total == 12
    assert result.unread == 3


def test_no_visibility_returns_empty(monkeypatch):
    monkeypatch.setattr(counts_mod, "check_permissions", lambda *a, **k: None)
    result = counts_mod.message_counts(MagicMock(user_id="u-1"), MagicMock())
    assert result == MessageCountsGet()


def test_sql_groups_and_hides_soft_deleted(monkeypatch):
    _, sql = _run(monkeypatch, [])
    assert "GROUP BY" in sql
    assert "message.archived_at IS NULL" in sql


def test_sql_excludes_own_posts_from_unread(monkeypatch):
    _, sql = _run(monkeypatch, [])
    assert "message.author_id !=" in sql


def test_sql_resolves_course_through_targets(monkeypatch):
    _, sql = _run(monkeypatch, [])
    assert "coalesce(message.course_id" in sql
    # One outer join per course-bearing target table.
    for table in ("course_content", "course_group", "submission_group", "course_member"):
        assert f"LEFT OUTER JOIN {table}" in sql, table


def test_counts_route_is_declared_before_the_id_route():
    from computor_backend.api.messages import messages_router
    paths = [route.path for route in messages_router.routes]
    assert "/counts" in paths and "/{id}" in paths
    assert paths.index("/counts") < paths.index("/{id}")
