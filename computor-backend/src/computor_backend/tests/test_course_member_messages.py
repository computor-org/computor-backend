"""Private course questions exercise real scope queries over synthetic records."""

from uuid import UUID
import pytest
from sqlalchemy import Boolean, Integer, create_engine, text
from sqlalchemy.orm import Session
from computor_backend.business_logic.messages import core
from computor_backend.business_logic.messages.audience import (
    get_message_recipient_user_ids,
)
from computor_backend.exceptions import ForbiddenException, BadRequestException
from computor_backend.interfaces.message import MessageInterface
from computor_backend.model import Base
from computor_backend.model.message import Message
from computor_backend.permissions.handlers_course import MessagePermissionHandler
from computor_backend.permissions.principal import Principal
from computor_backend.settings import settings
from computor_types.messages import MessageCreate, MessageQuery


def uid(number):
    return str(UUID(int=number))


OWNER, PEER, TUTOR, OTHER_TUTOR, ADMIN = [uid(i) for i in range(1, 6)]
COURSE, OTHER_COURSE, MEMBER, PEER_MEMBER = [uid(i) for i in range(11, 15)]


@pytest.fixture
def db(monkeypatch):
    # Only lookup columns, without unrelated PostgreSQL DDL/defaults.
    # Actual ORM permission, audience and target queries run unchanged.
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for name in [
            "user",
            "course",
            "course_member",
            "message",
            "user_role",
            "submission_group",
            "submission_group_member",
            "course_content",
            "course_group",
        ]:
            table = Base.metadata.tables[name]
            columns = ", ".join(
                f'"{c.name}" {"INTEGER" if isinstance(c.type, (Boolean, Integer)) else "TEXT"}'
                for c in table.columns
            )
            connection.execute(text(f'CREATE TABLE "{table.name}" ({columns})'))
        for user in [OWNER, PEER, TUTOR, OTHER_TUTOR, ADMIN]:
            connection.execute(
                text('INSERT INTO "user" (id, given_name) VALUES (:id, :name)'),
                {"id": user, "name": "Lena" if user == TUTOR else "Learner"},
            )
        for course in [COURSE, OTHER_COURSE]:
            connection.execute(
                text("INSERT INTO course (id, tutor_agent_auto_route) VALUES (:id, 1)"),
                {"id": course},
            )
        for member, user, course, role in [
            (MEMBER, OWNER, COURSE, "_student"),
            (PEER_MEMBER, PEER, COURSE, "_student"),
            (uid(20), TUTOR, COURSE, "_tutor"),
            (uid(21), OTHER_TUTOR, OTHER_COURSE, "_tutor"),
        ]:
            connection.execute(
                text(
                    "INSERT INTO course_member (id,user_id,course_id,course_role_id) VALUES (:id,:user,:course,:role)"
                ),
                {"id": member, "user": user, "course": course, "role": role},
            )
    monkeypatch.setattr(settings, "TUTOR_AGENT_USER_ID", TUTOR)
    with Session(engine) as session:
        yield session
    engine.dispose()


def principal(user):
    return Principal(user_id=user, is_admin=user == ADMIN)


def create(db, user=OWNER, **target):
    return core.create_message_with_author(
        MessageCreate(
            content="How should I start?", **(target or {"course_member_id": MEMBER})
        ),
        principal(user),
        db,
    )


@pytest.mark.parametrize("user", [OWNER, TUTOR, ADMIN])
def test_owner_same_course_tutor_and_admin_can_write(db, user):
    result = create(db, user)
    assert result["course_member_id"] == MEMBER
    assert result["title"] is None
    if user == OWNER:
        assert result["content"].startswith(f"@[Lena]({TUTOR}) ")


@pytest.mark.parametrize(
    "user,target",
    [(PEER, MEMBER), (OTHER_TUTOR, MEMBER), (OWNER, uid(999)), (ADMIN, uid(999))],
)
def test_other_students_cross_course_tutors_and_invalid_targets_are_forbidden(
    db, user, target
):
    with pytest.raises(ForbiddenException):
        create(db, user, course_member_id=target)


def test_private_question_reply_and_existing_read_list_audience_boundaries(db):
    question = Message(id=uid(100), visibility="public", **create(db))
    db.add(question)
    db.flush()
    reply_data = core.create_message_with_author(
        MessageCreate(
            content="Start with the course introduction.", parent_id=question.id
        ),
        principal(TUTOR),
        db,
    )
    assert reply_data["course_member_id"] == MEMBER
    assert reply_data["course_id"] is None
    assert reply_data["level"] == 1
    assert get_message_recipient_user_ids(question, db) == {OWNER, TUTOR}
    handler = MessagePermissionHandler(Message)
    for user in [OWNER, TUTOR, ADMIN, PEER, OTHER_TUTOR]:
        query = handler.build_query(principal(user), "get", db).filter(
            Message.id == question.id
        )
        assert bool(query.first()) == (user in {OWNER, TUTOR, ADMIN})
        listed = MessageInterface.search(
            db,
            handler.build_query(principal(user), "list", db),
            MessageQuery(course_id=COURSE, scope="course_member"),
        )
        assert bool(listed.first()) == (user in {OWNER, TUTOR, ADMIN})
    for action in ["update", "delete"]:
        assert (
            handler.build_query(principal(OWNER), action, db)
            .filter(Message.id == question.id)
            .first()
        )
        assert (
            not handler.build_query(principal(TUTOR), action, db)
            .filter(Message.id == question.id)
            .first()
        )
    with pytest.raises(ForbiddenException):
        core.create_message_with_author(
            MessageCreate(content="Not my thread", parent_id=question.id),
            principal(PEER),
            db,
        )


@pytest.mark.asyncio
async def test_private_member_channel_matches_message_audience(db):
    from computor_backend.websocket.connection_manager import ConnectionManager

    manager = ConnectionManager()
    for user in [OWNER, TUTOR, PEER, OTHER_TUTOR]:
        allowed, _reason = await manager._can_access_course_member(
            principal(user), MEMBER, db
        )
        assert allowed == (user in {OWNER, TUTOR})
    db.execute(
        text("UPDATE course_member SET course_role_id='_inactive' WHERE user_id=:id"),
        {"id": PEER},
    )
    assert not (await manager._can_access_course_member(principal(PEER), MEMBER, db))[0]


def test_explicit_recipients_preserve_audience_and_take_precedence(db):
    result = core.create_message_with_author(
        MessageCreate(content=f"@[Lena]({TUTOR}) please help", course_member_id=MEMBER),
        principal(OWNER),
        db,
    )
    assert result["content"] == f"@[Lena]({TUTOR}) please help"
    with pytest.raises(BadRequestException):
        core.create_message_with_author(
            MessageCreate(
                content=f"@[Peer]({PEER}) please help", course_member_id=MEMBER
            ),
            principal(OWNER),
            db,
        )


def test_private_conversation_cannot_import_a_parent_from_another_scope(db):
    hidden = Message(
        id=uid(101),
        visibility="public",
        author_id=PEER,
        submission_group_id=uid(102),
        content="Private work",
        level=0,
    )
    db.add(hidden)
    db.flush()
    with pytest.raises(BadRequestException):
        core.create_message_with_author(
            MessageCreate(
                content="Reply", course_member_id=MEMBER, parent_id=hidden.id
            ),
            principal(OWNER),
            db,
        )


@pytest.mark.parametrize("user", [OWNER, TUTOR, ADMIN])
def test_inactive_target_membership_cannot_start_or_receive_new_questions(db, user):
    db.execute(
        text("UPDATE course_member SET course_role_id='_inactive' WHERE id=:id"),
        {"id": MEMBER},
    )
    with pytest.raises(ForbiddenException):
        create(db, user)
