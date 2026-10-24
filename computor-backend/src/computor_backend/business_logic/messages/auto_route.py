"""Address unmentioned student messages to the tutor agent.

A course with ``tutor_agent_auto_route`` set routes every student message that
mentions nobody to the configured tutor agent (``TUTOR_AGENT_USER_ID``, shown
as Lena) by prepending a visible ``@[Lena](<uuid>)`` mention. From there it is
an ordinary mention: the audience gate validates it and ``message_mention``
rows record it, so the agent picks it up with its existing ``mentions_me``
query and no worker change is needed.
"""
from typing import Optional

from sqlalchemy.orm import Session

from computor_backend.model.auth import User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
)
from computor_backend.settings import settings
from .mentions import extract_mention_user_ids, mention_ref, message_audience_user_ids


def _course_id_for_targets(model_dump: dict, db: Session) -> Optional[str]:
    """The course of a not-yet-persisted message, from its target ids."""
    if model_dump.get('course_id'):
        return str(model_dump['course_id'])
    for key, model in (
        ('course_member_id', CourseMember),
        ('submission_group_id', SubmissionGroup),
        ('course_content_id', CourseContent),
        ('course_group_id', CourseGroup),
    ):
        target = model_dump.get(key)
        if target:
            row = db.query(model.course_id).filter(model.id == target).first()
            return str(row[0]) if row else None
    return None


def _auto_route_enabled(course_id: str, db: Session) -> bool:
    return bool(
        db.query(Course.tutor_agent_auto_route).filter(Course.id == course_id).scalar()
    )


def _course_role(course_id: str, user_id, db: Session) -> Optional[str]:
    return (
        db.query(CourseMember.course_role_id)
        .filter(CourseMember.course_id == course_id, CourseMember.user_id == user_id)
        .scalar()
    )


def _active_user(user_id: str, db: Session) -> Optional[User]:
    return (
        db.query(User)
        .filter(User.id == user_id, User.archived_at.is_(None), User.banned_at.is_(None))
        .first()
    )


def route_to_tutor_agent(
    message_like,
    model_dump: dict,
    author_id,
    parent_message,
    db: Session,
) -> Optional[str]:
    """Return the message content, with a leading tutor mention if this
    message should be routed to the tutor agent; otherwise unchanged.

    Routes only when all of these hold: a tutor agent is configured and
    active, the content mentions nobody (plain ``@lena`` was already resolved
    to a mention by the caller), the author is a ``_student`` of a course
    with ``tutor_agent_auto_route`` set, the message is not a reply to the
    agent (its follow-up handling already covers those), and the agent is in
    the message's audience.
    """
    content = model_dump.get('content')
    tutor = settings.TUTOR_AGENT_USER_ID
    if not tutor or not content or not content.strip():
        return content
    tutor = tutor.lower()
    if str(author_id).lower() == tutor or extract_mention_user_ids(content):
        return content
    if parent_message is not None and str(parent_message.author_id).lower() == tutor:
        return content

    course_id = _course_id_for_targets(model_dump, db)
    if course_id is None or not _auto_route_enabled(course_id, db):
        return content
    if _course_role(course_id, author_id, db) != '_student':
        return content

    audience = message_audience_user_ids(message_like, db)
    if audience is not None and tutor not in {str(a).lower() for a in audience}:
        return content
    agent = _active_user(tutor, db)
    if agent is None:
        return content
    ref = mention_ref(agent)
    return f"@[{ref.given_name}]({ref.id}) {content}"
