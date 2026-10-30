"""Plain mentions and compatibility aliases use the authorized existing identity."""
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from computor_backend.business_logic.messages import mentions
from computor_backend.business_logic.messages.mention_text import resolve_plain_mentions
from computor_backend.exceptions import BadRequestException
from computor_backend.model.auth import Profile, User
from computor_backend.business_logic.messages import core
from computor_backend.permissions.principal import Principal
from computor_types.messages import MessageCreate, MessageGet, MessageUpdate


TUTOR = "12345678-1234-1234-1234-123456789abc"
HUMAN = "12345678-1234-1234-1234-123456789def"
OTHER = "12345678-1234-1234-1234-123456789aaa"
TOKEN = f"@[Lena Tutor]({TUTOR})"


@pytest.mark.parametrize("alias", ["lena", "luna", "ai", "LENA", "Luna", "AI"])
def test_each_plain_alias_resolves(alias):
    result = resolve_plain_mentions(f"@{alias} Can you explain this?", lambda name: (TUTOR, "Lena Tutor"))
    assert result == f"{TOKEN} Can you explain this?"


@pytest.mark.parametrize("content", [
    "mail@lena", "mail@lena.example", r"\@lena", "`@lena`", "``@lena `code` ``",
    "```python\n@lena\n```", "~~~\n@lena\n~~~", "    @lena", "\t@lena",
    "@lena@example.org", f"@[Luna Tutor]({TUTOR})",
    "see https://medium.com/@ai now", "<https://example.org/@lena>",
    "www.example.org/@luna", "docs/@ai",
])
def test_literals_do_not_resolve_or_lookup(content):
    lookup = MagicMock()
    assert resolve_plain_mentions(content, lookup) == content
    lookup.assert_not_called()


def test_prose_after_code_and_punctuation_resolve():
    content = "```\n@luna\n```\nPlease ask (@ai), then @lena."
    result = resolve_plain_mentions(content, lambda name: (TUTOR, "Lena Tutor"))
    assert result == f"```\n@luna\n```\nPlease ask ({TOKEN}), then {TOKEN}."


def test_lookup_key_matches_sql_lower_not_casefold():
    seen = []
    resolve_plain_mentions("@Strauß", lambda name: seen.append(name))
    assert seen == ["strauß"]


def test_unknown_and_substring_tokens_stay_plain():
    def lookup(name):
        return (TUTOR, "Lena Tutor") if name in {"lena", "luna", "ai"} else None
    content = "@lenabelle @lunatic @aimee @unknown"
    assert resolve_plain_mentions(content, lookup) == content


def _create_profile_table(connection):
    # Message create reads the author's profile language.
    columns = ", ".join(f'"{c.name}" TEXT' for c in Profile.__table__.columns)
    connection.execute(text(f'CREATE TABLE "profile" ({columns})'))


@pytest.fixture
def audience_db(monkeypatch):
    """Real SQL lookups over synthetic users, with a controlled audience boundary.

    Only lookup columns are exercised. SQLite storage avoids requiring the
    PostgreSQL-only unrelated tables in the full application schema.
    """
    engine = create_engine("sqlite://")
    columns = ", ".join(f'"{c.name}" TEXT' for c in User.__table__.columns)
    with engine.begin() as connection:
        connection.execute(text(f'CREATE TABLE "user" ({columns})'))
        _create_profile_table(connection)
        for uid, given, family in [(TUTOR, "Luna", "Tutor"), (HUMAN, "Lena", "Human"), (OTHER, "Max", "Human")]:
            connection.execute(text('INSERT INTO "user" (id, given_name, family_name) VALUES (:id, :given, :family)'),
                               {"id": uid, "given": given, "family": family})
    monkeypatch.setattr(mentions.settings, "TUTOR_AGENT_USER_ID", TUTOR)
    monkeypatch.setattr(mentions, "message_audience_user_ids", lambda _m, _db: {TUTOR, HUMAN, OTHER})
    with Session(engine) as db:
        yield db
    engine.dispose()


def test_three_aliases_deduplicate_to_one_tutor_even_with_human_lena(audience_db):
    result = mentions.resolve_message_mentions(None, "@lena @luna @ai", audience_db)
    assert result == f"{TOKEN} {TOKEN} {TOKEN}"
    assert mentions.extract_mention_user_ids(result) == [TUTOR]


def test_missing_audience_membership_never_falls_back_to_human(audience_db, monkeypatch):
    monkeypatch.setattr(mentions, "message_audience_user_ids", lambda _m, _db: {HUMAN})
    assert mentions.resolve_message_mentions(None, "@lena @luna @ai", audience_db) == "@lena @luna @ai"
    assert mentions.list_mentionable_users(None, audience_db, search="ai") == []


@pytest.mark.parametrize("column", ["archived_at", "banned_at"])
def test_inactive_tutor_is_not_resolved_or_autocompleted(audience_db, column):
    audience_db.execute(text(f'UPDATE "user" SET {column} = :date WHERE id = :id'),
                        {"id": TUTOR, "date": "2026-10-14 00:00:00"})
    assert mentions.resolve_message_mentions(None, "@ai", audience_db) == "@ai"
    assert mentions.list_mentionable_users(None, audience_db, search="ai") == []


def test_unconfigured_alias_is_not_a_human_name(audience_db, monkeypatch):
    monkeypatch.setattr(mentions.settings, "TUTOR_AGENT_USER_ID", None)
    assert mentions.resolve_message_mentions(None, "@lena", audience_db) == "@lena"


def test_duplicate_human_names_require_selection(audience_db):
    with pytest.raises(BadRequestException, match="ambiguous"):
        mentions.resolve_message_mentions(None, "@human help", audience_db)


def test_exact_human_name_uses_the_human_id(audience_db):
    assert mentions.resolve_message_mentions(None, "@max help", audience_db) == f"@[Max Human]({OTHER}) help"


@pytest.mark.parametrize("query", ["lena", "luna", "ai", "AI", "lu"])
def test_autocomplete_aliases_offer_one_canonical_tutor(audience_db, query):
    users = mentions.list_mentionable_users(None, audience_db, search=query)
    refs = [mentions.mention_ref(user) for user in users]
    tutors = [ref for ref in refs if ref.id == TUTOR]
    assert len(tutors) == 1
    assert tutors[0].given_name == "Lena"
    assert tutors[0].aliases == ["lena", "luna", "ai"]
    for ref in refs:
        if ref.id != TUTOR:
            assert ref.aliases == []


def test_exact_tutor_handle_cannot_be_crowded_out_by_same_named_humans(audience_db):
    users = mentions.list_mentionable_users(None, audience_db, search="lena", limit=1)
    assert [str(user.id) for user in users] == [TUTOR]


def test_exact_tutor_handle_keeps_same_named_humans_selectable(audience_db):
    users = mentions.list_mentionable_users(None, audience_db, search="lena")
    assert [str(user.id) for user in users] == [TUTOR, HUMAN]


def test_unconfigured_tutor_does_not_hide_human_names(audience_db, monkeypatch):
    monkeypatch.setattr(mentions.settings, "TUTOR_AGENT_USER_ID", None)
    users = mentions.list_mentionable_users(None, audience_db, search="lena")
    assert [str(user.id) for user in users] == [HUMAN]


def test_create_and_reply_normalize_content_after_resolving_scope(audience_db, monkeypatch):
    group = "22222222-2222-2222-2222-222222222222"
    parent_id = "33333333-3333-3333-3333-333333333333"
    monkeypatch.setattr(core, "_check_submission_group_write_permission", lambda *args: None)
    principal = Principal(user_id=HUMAN)
    created = core.create_message_with_author(MessageCreate(content="@ai help", submission_group_id=group), principal, audience_db)
    assert created["content"] == f"{TOKEN} help"
    assert created["submission_group_id"] == group

    parent = SimpleNamespace(id=parent_id, submission_group_id=group, level=0)
    real_query = audience_db.query
    from computor_backend.model.message import Message
    def query(*columns):
        if len(columns) == 1 and columns[0] is Message:
            result = MagicMock()
            result.filter.return_value.first.return_value = parent
            return result
        return real_query(*columns)
    monkeypatch.setattr(audience_db, "query", query)
    reply = core.create_message_with_author(MessageCreate(content="@luna follow-up", parent_id=parent_id), principal, audience_db)
    assert reply["submission_group_id"] == group
    assert reply["content"] == f"{TOKEN} follow-up"


@pytest.mark.asyncio
async def test_create_and_edit_api_persist_the_resolved_mention_content(audience_db, monkeypatch):
    from computor_backend.api import messages as api

    group = "22222222-2222-2222-2222-222222222222"
    message_id = "33333333-3333-3333-3333-333333333333"
    monkeypatch.setattr(core, "_check_submission_group_write_permission", lambda *args: None)
    principal = Principal(user_id=HUMAN)

    async def create(_principal, _db, entity, *_interfaces, before_commit):
        before_commit(SimpleNamespace(id=message_id), _db)
        return MessageGet(id=message_id, author_id=HUMAN, content=entity.content,
                          submission_group_id=group, level=0)
    monkeypatch.setattr(api, "create_db", create)
    monkeypatch.setattr(api, "mark_author_as_reader", lambda *args, **kwargs: None)
    repository = MagicMock()
    repository.get_by_id_optional.return_value = None
    monkeypatch.setattr(api, "MessageRepository", lambda *args: repository)
    monkeypatch.setattr(api, "get_message_with_read_status", lambda _id, message, *_args: message)
    monkeypatch.setattr(api.ws_broadcast, "message_created", AsyncMock())
    monkeypatch.setattr(api.ws_broadcast, "message_updated", AsyncMock())
    sync = MagicMock()
    monkeypatch.setattr(api, "sync_message_mentions", sync)

    payload = MessageCreate(content="@ai new message", submission_group_id=group)
    created = await api.create_message(principal, payload, audience_db, MagicMock())
    assert created.content == f"{TOKEN} new message"
    assert sync.call_args.args[1] == created.content

    monkeypatch.setattr(api, "get_id_db", AsyncMock(return_value=created))
    update = MagicMock(side_effect=lambda **kwargs: created.model_copy(update={"content": kwargs["new_content"]}))
    monkeypatch.setattr(api, "update_message_with_audit", update)
    edited = await api.update_message(message_id, MessageUpdate(content="@luna edited"), principal, audience_db)
    assert edited.content == f"{TOKEN} edited"
    assert update.call_args.kwargs["new_content"] == edited.content


@pytest.fixture
def message_db(tmp_path, monkeypatch):
    """File-backed SQLite, so a second connection sees exactly what was committed."""
    from uuid import uuid4

    from sqlalchemy import event

    from computor_backend.model.message import Message, MessageMention, MessageRead
    from computor_backend.model.message_audit import MessageAuditLog

    models = [Message, MessageRead, MessageMention, MessageAuditLog]
    engine = create_engine(f"sqlite:///{tmp_path / 'messages.db'}", connect_args={"check_same_thread": False})
    with engine.begin() as connection:
        for model in models:
            columns = ", ".join(
                f'"{c.name}" TEXT' + (" PRIMARY KEY" if c.name == "id" else "")
                + (" DEFAULT CURRENT_TIMESTAMP" if c.name == "created_at" else "")
                for c in model.__table__.columns
            )
            connection.execute(text(f'CREATE TABLE "{model.__tablename__}" ({columns})'))
        columns = ", ".join(f'"{c.name}" TEXT' for c in User.__table__.columns)
        connection.execute(text(f'CREATE TABLE "user" ({columns})'))
        _create_profile_table(connection)
        connection.execute(text('INSERT INTO "user" (id, given_name, family_name) VALUES (:id, \'Lena\', \'Human\')'),
                           {"id": HUMAN})

    # SQLite stands in for PostgreSQL's uuid_generate_v4() server default.
    def assign_id(_mapper, _connection, target):
        target.id = target.id or str(uuid4())
    for model in models:
        event.listen(model, "before_insert", assign_id)
    monkeypatch.setattr(mentions.settings, "TUTOR_AGENT_USER_ID", TUTOR)
    with Session(engine) as db:
        yield engine, db
    for model in models:
        event.remove(model, "before_insert", assign_id)
    engine.dispose()


def _committed_states(engine, db):
    """Record, at every commit of ``db``, what any other reader can see."""
    from sqlalchemy import event

    states = []

    def snapshot(_session):
        with engine.connect() as reader:
            states.append({
                "messages": dict(reader.execute(text("SELECT id, content FROM message")).all()),
                "mentions": set(reader.execute(text("SELECT message_id, mentioned_user_id FROM message_mention")).all()),
                "reads": set(reader.execute(text("SELECT message_id, reader_user_id FROM message_read")).all()),
            })
    event.listen(db, "after_commit", snapshot)
    return states


def _mentions_of(state, message_id):
    return {user for mid, user in state["mentions"] if mid == message_id}


@pytest.mark.asyncio
async def test_new_message_is_never_visible_without_its_mentions_and_read_mark(message_db, monkeypatch):
    from computor_backend.api import messages as api
    from computor_backend.business_logic import crud

    engine, db = message_db
    group = "22222222-2222-2222-2222-222222222222"
    content = f"{TOKEN} can you explain this?"
    monkeypatch.setattr(api, "create_message_with_author", lambda *_args: {
        "content": content, "submission_group_id": group, "author_id": HUMAN, "level": 0})
    monkeypatch.setattr(crud, "set_db_user", lambda *_args: None)
    handler = MagicMock()
    handler.can_perform_action.return_value = True
    monkeypatch.setattr(crud.permission_registry, "get_handler", lambda _model: handler)
    repository = MagicMock()
    repository.get_by_id_optional.return_value = None
    monkeypatch.setattr(api, "MessageRepository", lambda *args: repository)
    monkeypatch.setattr(api, "get_message_with_read_status", lambda _id, message, *_args: message)
    monkeypatch.setattr(api.ws_broadcast, "message_created", AsyncMock())
    states = _committed_states(engine, db)

    created = await api.create_message(
        Principal(user_id=HUMAN), MessageCreate(content=content, submission_group_id=group), db, MagicMock())

    message_id = str(created.id)
    visible = [state for state in states if message_id in state["messages"]]
    assert visible
    for state in visible:
        assert _mentions_of(state, message_id) == {TUTOR}
        assert (message_id, HUMAN) in state["reads"]


def test_edited_content_is_never_visible_with_stale_mentions(message_db):
    from computor_backend.business_logic.messages import lifecycle

    engine, db = message_db
    message_id = "44444444-4444-4444-4444-444444444444"
    db.execute(text("INSERT INTO message (id, author_id, content) VALUES (:id, :author, :content)"),
               {"id": message_id, "author": HUMAN, "content": f"@[Max Human]({OTHER}) hi"})
    db.execute(text("INSERT INTO message_mention (id, message_id, mentioned_user_id) VALUES (:id, :id, :user)"),
               {"id": message_id, "user": OTHER})
    db.commit()
    states = _committed_states(engine, db)

    lifecycle.update_message_with_audit(
        message_id=message_id, principal=Principal(user_id=HUMAN), db=db, new_content=f"{TOKEN} hi")

    assert states
    for state in states:
        expected = set(mentions.extract_mention_user_ids(state["messages"][message_id]))
        assert _mentions_of(state, message_id) == expected
