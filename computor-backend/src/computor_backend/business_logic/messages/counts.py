"""Aggregated message counts per (scope, course) — ``GET /messages/counts``.

One GROUP BY over the caller's full read visibility. The base query comes
from ``MessagePermissionHandler.build_query`` via ``check_permissions`` —
the exact filter ``GET /messages`` lists through — so the numbers can never
drift from what the caller could actually page. The unread definition
matches the dashboard CTE in ``repositories/course_content_subqueries``:
no read row for the caller, and not authored by them.
"""
from typing import Dict, Optional, Tuple

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session, aliased

from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.principal import Principal
from computor_backend.model.course import (
    CourseContent,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
)
from computor_backend.model.message import Message, MessageRead
from computor_types.messages import (
    MESSAGE_TARGET_FIELDS,
    MessageCountsGet,
    MessageScopeCounts,
)


def message_counts(permissions: Principal, db: Session) -> MessageCountsGet:
    """Count visible messages, grouped by scope and resolved course."""
    query = check_permissions(permissions, Message, "list", db)
    if query is None:
        return MessageCountsGet()

    uid = str(permissions.user_id) if permissions.user_id else None

    # ``field`` is "<scope>_id"; first set target wins, mirroring
    # ``scope_for_targets`` (exact for post-invariant rows, correct by
    # priority for legacy multi-target rows).
    scope_expr = case(
        *[
            (getattr(Message, field).isnot(None), field[:-3])
            for field in MESSAGE_TARGET_FIELDS
        ],
        else_="global",
    )

    # SQL twin of ``audience.course_ids_for_messages``: the course is either
    # stamped on the message or reached through its target.
    cc = aliased(CourseContent)
    cg = aliased(CourseGroup)
    sg = aliased(SubmissionGroup)
    cm = aliased(CourseMember)
    course_expr = func.coalesce(
        Message.course_id, cc.course_id, cg.course_id, sg.course_id, cm.course_id
    )

    read = aliased(MessageRead)
    unread_case = case(
        (and_(read.id.is_(None), Message.author_id != uid), 1),
        else_=0,
    )

    rows = (
        query
        .outerjoin(cc, cc.id == Message.course_content_id)
        .outerjoin(cg, cg.id == Message.course_group_id)
        .outerjoin(sg, sg.id == Message.submission_group_id)
        .outerjoin(cm, cm.id == Message.course_member_id)
        .outerjoin(read, and_(read.message_id == Message.id, read.reader_user_id == uid))
        .filter(Message.archived_at.is_(None))
        .with_entities(
            scope_expr.label("scope"),
            course_expr.label("course_id"),
            func.count(Message.id).label("total"),
            func.coalesce(func.sum(unread_case), 0).label("unread"),
        )
        .group_by(scope_expr, course_expr)
        .all()
    )

    cells: Dict[Tuple[str, Optional[str]], MessageScopeCounts] = {}
    for scope, course_id, total, unread in rows:
        cells[(scope, str(course_id) if course_id else None)] = MessageScopeCounts(
            scope=scope,
            course_id=str(course_id) if course_id else None,
            total=int(total),
            unread=int(unread),
        )

    counts = [cells[key] for key in sorted(cells, key=lambda k: (k[0], k[1] or ""))]
    return MessageCountsGet(
        counts=counts,
        total=sum(c.total for c in counts),
        unread=sum(c.unread for c in counts),
    )
