"""Soft-deleted messages must not come back from ``GET /messages``.

``soft_delete_message`` keeps the row so replies stay attached to their
thread, and every read path is expected to hide it. ``get_message_thread``
and the unread CTEs did; ``MessageInterface.search`` — the one the list
endpoint runs — did not, so a message the user had just deleted reappeared on
the next refetch (computor-org/issues#288).

These tests compile the query rather than execute it: the filter is a
property of the SQL ``search`` builds, and asserting on it needs no database.
"""

from unittest.mock import MagicMock

from sqlalchemy.orm import Query

from computor_backend.interfaces.message import MessageInterface
from computor_backend.model.message import Message
from computor_types.messages import MessageQuery


def _sql(params) -> str:
    """The WHERE clause ``search`` produces for these query params."""
    query = MessageInterface.search(MagicMock(), Query([Message]), params)
    return str(query.statement.compile(compile_kwargs={"literal_binds": True}))


ARCHIVED_IS_NULL = "message.archived_at IS NULL"


def test_default_query_hides_soft_deleted() -> None:
    assert ARCHIVED_IS_NULL in _sql(MessageQuery())


def test_no_params_hides_soft_deleted() -> None:
    """The ``params is None`` path returns early — the filter has to precede it."""
    assert ARCHIVED_IS_NULL in _sql(None)


def test_include_deleted_opts_back_in() -> None:
    """Audit/moderation views can still ask for the tombstones."""
    assert ARCHIVED_IS_NULL not in _sql(MessageQuery(include_deleted=True))


def test_filter_survives_other_filters() -> None:
    """A target filter must narrow the live rows, not replace the archived check."""
    sql = _sql(MessageQuery(author_id="11111111-1111-1111-1111-111111111111"))
    assert ARCHIVED_IS_NULL in sql
    assert "message.author_id" in sql


def test_deleted_by_is_none_while_live() -> None:
    """A live message has no deleter; claiming 'author' made it look deleted."""
    live = Message()
    assert live.is_deleted is False
    assert live.deleted_by is None
    assert live.deletion_reason is None
