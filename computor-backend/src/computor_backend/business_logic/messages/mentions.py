"""@mention extraction, audience-gating and message_mention reconciliation.

A mention is stored inline in ``Message.content`` as ``@[Given Family](<uuid>)``
(the uuid is authoritative). On write we extract the uuids, confirm each
mentioned user is in the message's audience — reusing
``get_message_recipient_user_ids`` so the gate can never disagree with read
visibility — then reconcile the ``message_mention`` rows that power fast
"mentions of me" lookups.
"""
import re
from typing import Optional, List, Dict
from sqlalchemy import or_
from sqlalchemy.orm import Session

from computor_backend.exceptions import BadRequestException
from computor_backend.model.message import Message, MessageMention
from computor_backend.model.course import CourseMember
from computor_backend.model.auth import User
from computor_types.messages import MessageMentionRef
from .audience import get_message_recipient_user_ids


MENTION_PATTERN = re.compile(r'@\[[^\]]*\]\(([0-9a-fA-F-]{36})\)')


_MENTION_TARGET_ATTRS = (
    'user_id', 'course_member_id', 'submission_group_id', 'course_group_id',
    'course_content_id', 'course_id', 'course_family_id', 'organization_id',
)


def extract_mention_user_ids(content: Optional[str]) -> list[str]:
    """Extract mentioned user ids from ``@[name](<uuid>)`` tokens in content.

    The uuid is authoritative; the bracketed display name is ignored. Ids are
    lower-cased and de-duplicated, preserving first-seen order.
    """
    if not content:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in MENTION_PATTERN.findall(content):
        uid = raw.lower()
        if uid not in seen:
            seen.add(uid)
            ordered.append(uid)
    return ordered


def _transient_message_for_targets(model_dump: dict, author_id) -> Message:
    """Build an unsaved Message carrying just the target ids + author that the
    audience query reads, so the create-time gate can run before persistence."""
    return Message(
        author_id=author_id,
        user_id=model_dump.get('user_id'),
        course_member_id=model_dump.get('course_member_id'),
        submission_group_id=model_dump.get('submission_group_id'),
        course_group_id=model_dump.get('course_group_id'),
        course_content_id=model_dump.get('course_content_id'),
        course_id=model_dump.get('course_id'),
        course_family_id=model_dump.get('course_family_id'),
        organization_id=model_dump.get('organization_id'),
    )


def message_audience_user_ids(message_like, db: Session) -> Optional[set[str]]:
    """User ids allowed to see ``message_like``, or ``None`` for global
    (everyone). Thin wrapper over ``get_message_recipient_user_ids`` — the
    canonical inverse of ``MessagePermissionHandler``."""
    if not any(getattr(message_like, attr, None) for attr in _MENTION_TARGET_ATTRS):
        return None  # global → everyone
    # Mentionability is narrower than read-visibility: a global admin (or any
    # privilege-bypass viewer) who isn't actually a participant of the scope —
    # e.g. not a member of the submission group / course — must not be
    # mentionable. They keep READ access; they're just not offered as a mention
    # target nor accepted by the gate.
    return get_message_recipient_user_ids(message_like, db, include_global_admins=False)


def validate_message_mentions(message_like, content: Optional[str], db: Session) -> list[str]:
    """Confirm every @mention in ``content`` resolves to a real user who is in
    ``message_like``'s audience; return the validated user ids.

    Raises ``BadRequestException`` (listing the offenders) if a mention is
    unresolvable or points at someone who could not see the message — you
    cannot mention a user who has no visibility of the message.
    """
    mentioned = extract_mention_user_ids(content)
    if not mentioned:
        return []

    existing = {
        str(r[0]).lower()
        for r in db.query(User.id).filter(User.id.in_(mentioned)).all()
    }
    unresolved = [uid for uid in mentioned if uid not in existing]

    audience = message_audience_user_ids(message_like, db)
    if audience is None:
        not_permitted: list[str] = []
    else:
        audience_lower = {a.lower() for a in audience}
        not_permitted = [
            uid for uid in mentioned
            if uid in existing and uid not in audience_lower
        ]

    if unresolved or not_permitted:
        raise BadRequestException(detail={
            "message": "Some mentioned users are invalid or cannot see this message.",
            "unresolved": unresolved,
            "not_permitted": not_permitted,
        })

    return mentioned


def sync_message_mentions(message_id, content: Optional[str], db: Session) -> None:
    """Reconcile ``message_mention`` rows for a message to match the mentions
    currently in its content (add new, drop removed). Commits on change."""
    desired = set(extract_mention_user_ids(content))
    existing_rows = db.query(MessageMention).filter(
        MessageMention.message_id == message_id
    ).all()
    existing = {str(r.mentioned_user_id).lower(): r for r in existing_rows}

    changed = False
    for uid in desired:
        if uid not in existing:
            db.add(MessageMention(message_id=message_id, mentioned_user_id=uid))
            changed = True
    for uid, row in existing.items():
        if uid not in desired:
            db.delete(row)
            changed = True

    if changed:
        db.commit()


def list_mentionable_users(
    message_like,
    db: Session,
    search: Optional[str] = None,
    limit: int = 50,
) -> List[User]:
    """Users who may be @mentioned in a message with ``message_like``'s scope —
    i.e. its audience — optionally narrowed by a name search."""
    audience = message_audience_user_ids(message_like, db)
    q = db.query(User).filter(User.archived_at.is_(None))
    if audience is not None:
        if not audience:
            return []
        q = q.filter(User.id.in_(audience))
    if search:
        like = f"%{search}%"
        q = q.filter(or_(User.given_name.ilike(like), User.family_name.ilike(like)))
    q = q.order_by(User.family_name, User.given_name)
    return q.limit(limit).all()


def _course_id_for_message(msg: Message):
    """The course a message belongs to (for resolving a participant's role),
    or None for user-direct / family / org / global scopes."""
    if msg.course_id:
        return msg.course_id
    if msg.course_content_id and msg.course_content:
        return msg.course_content.course_id
    if msg.course_group_id and msg.course_group:
        return msg.course_group.course_id
    if msg.submission_group_id and msg.submission_group:
        return msg.submission_group.course_id
    if msg.course_member_id and msg.course_member:
        return msg.course_member.course_id
    return None


def _get_mentions_info(db_messages: List[Message], db: Session) -> Dict[str, List[MessageMentionRef]]:
    """Batch-load mention refs (id, name, and the mentioned user's course role
    within the message's course) for a set of messages."""
    if not db_messages:
        return {}
    msg_ids = [str(m.id) for m in db_messages]
    rows = (
        db.query(
            MessageMention.message_id, User.id, User.given_name, User.family_name
        )
        .join(User, User.id == MessageMention.mentioned_user_id)
        .filter(MessageMention.message_id.in_(msg_ids))
        .all()
    )

    # Resolve each message's course so the mentioned user's role can be attached.
    course_by_msg = {str(m.id): _course_id_for_message(m) for m in db_messages}
    user_ids = {str(u) for (_mid, u, _g, _f) in rows}
    course_ids = {str(c) for c in course_by_msg.values() if c}
    role_map: Dict[tuple, str] = {}
    if user_ids and course_ids:
        for c, u, role_id in (
            db.query(CourseMember.course_id, CourseMember.user_id, CourseMember.course_role_id)
            .filter(CourseMember.course_id.in_(course_ids), CourseMember.user_id.in_(user_ids))
            .all()
        ):
            role_map[(str(c), str(u))] = role_id

    result: Dict[str, List[MessageMentionRef]] = {mid: [] for mid in msg_ids}
    for message_id, user_id, given, family in rows:
        mid = str(message_id)
        cid = course_by_msg.get(mid)
        role = role_map.get((str(cid), str(user_id))) if cid else None
        result.setdefault(mid, []).append(
            MessageMentionRef(
                id=str(user_id), given_name=given, family_name=family, course_role_id=role
            )
        )
    return result
