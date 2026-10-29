"""A new message carries its author's reading language (issues#556).

The tutor reads the assignment in this language, so it must be resolved
exactly like GET /user's ``effective_language``: profile language first,
else the request's Accept-Language.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.dependencies.utils import get_dependant
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from computor_backend.model.auth import Profile, User
from computor_backend.model.message import Message, MessageMention, MessageRead
from computor_backend.model.message_audit import MessageAuditLog
from computor_backend.permissions.principal import Principal
from computor_types.messages import MessageCreate, MessageList


AUTHOR = "12345678-1234-1234-1234-123456789def"
GROUP = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def message_db(tmp_path):
    models = [Message, MessageRead, MessageMention, MessageAuditLog]
    engine = create_engine(f"sqlite:///{tmp_path / 'messages.db'}", connect_args={"check_same_thread": False})
    with engine.begin() as connection:
        for model in models + [User, Profile]:
            columns = ", ".join(
                f'"{c.name}" TEXT' + (" PRIMARY KEY" if c.name == "id" else "")
                + (" DEFAULT CURRENT_TIMESTAMP" if c.name == "created_at" else "")
                for c in model.__table__.columns
            )
            connection.execute(text(f'CREATE TABLE "{model.__tablename__}" ({columns})'))
        connection.execute(text('INSERT INTO "user" (id, given_name) VALUES (:id, \'Ada\')'), {"id": AUTHOR})

    # SQLite stands in for PostgreSQL's uuid_generate_v4() server default.
    def assign_id(_mapper, _connection, target):
        target.id = target.id or str(uuid4())
    for model in models:
        event.listen(model, "before_insert", assign_id)
    with Session(engine) as db:
        yield db
    for model in models:
        event.remove(model, "before_insert", assign_id)
    engine.dispose()


async def _post(db, monkeypatch, accept_language):
    from computor_backend.api import messages as api
    from computor_backend.business_logic import crud

    monkeypatch.setattr(api, "create_message_with_author", lambda *_args: {
        "content": "Why does my loop not stop?", "submission_group_id": GROUP,
        "author_id": AUTHOR, "level": 0})
    monkeypatch.setattr(crud, "set_db_user", lambda *_args: None)
    handler = MagicMock()
    handler.can_perform_action.return_value = True
    monkeypatch.setattr(crud.permission_registry, "get_handler", lambda _model: handler)
    repository = MagicMock()
    repository.get_by_id_optional.return_value = None
    monkeypatch.setattr(api, "MessageRepository", lambda *args: repository)
    monkeypatch.setattr(api, "get_message_with_read_status", lambda _id, message, *_args: message)
    monkeypatch.setattr(api.ws_broadcast, "message_created", AsyncMock())

    headers = {"Accept-Language": accept_language} if accept_language else {}
    return await api.create_message(
        Principal(user_id=AUTHOR), MessageCreate(content="x", submission_group_id=GROUP),
        db, MagicMock(), http_request=SimpleNamespace(headers=headers))


@pytest.mark.asyncio
@pytest.mark.parametrize("profile_language, accept_language, expected", [
    ("en", "de-AT,de;q=0.9", "en"),   # profile wins over the browser
    ("de", "en-US,en;q=0.9", "de"),
    (None, "en-US,en;q=0.9", "en"),   # no profile: browser decides
    (None, "de-AT", "de"),
    (None, "fr-FR", "en"),
    (None, None, "de"),
])
async def test_create_stores_and_returns_the_reading_language(
    message_db, monkeypatch, profile_language, accept_language, expected,
):
    if profile_language:
        message_db.execute(
            text('INSERT INTO profile (id, user_id, language_code) VALUES (:id, :user, :lang)'),
            {"id": str(uuid4()), "user": AUTHOR, "lang": profile_language})
        message_db.commit()

    created = await _post(message_db, monkeypatch, accept_language)

    assert created.reading_language == expected
    stored = message_db.execute(
        text("SELECT reading_language FROM message WHERE id = :id"), {"id": str(created.id)}
    ).scalar_one()
    assert stored == expected
    row = message_db.query(Message).filter(Message.id == str(created.id)).one()
    assert MessageList.model_validate(row, from_attributes=True).reading_language == expected


def test_fastapi_injects_the_request_into_create_message():
    from computor_backend.api import messages as api

    assert get_dependant(path="/messages", call=api.create_message).request_param_name == "http_request"
