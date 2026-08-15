"""Server-side message context enrichment (issue #322).

A message row carries exactly one target id — the single-target invariant
nulls every other column on create — so clients could only ever render the
raw UUID ("Submission Group e86522aa"). This module resolves the human
identity around each message in a fixed number of queries per page: the
course title, the course content (for submission-group messages reached
through ``SubmissionGroup.course_content_id``), the course group title, and
the submission group's members.
"""
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from computor_backend.model.auth import User
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.message import Message
from computor_types.messages import MessageContext, MessageContextMember


def message_contexts_for(
    db_messages: List[Message],
    db: Session,
    course_by_message: Optional[Dict[str, Optional[str]]] = None,
) -> Dict[str, Optional[MessageContext]]:
    """Resolve a :class:`MessageContext` per message, batched.

    ``course_by_message`` is the map produced by
    :func:`~computor_backend.business_logic.messages.audience.course_ids_for_messages`;
    pass it in when the caller already computed it (the author enricher
    does) so the page resolves courses once, not twice.

    At most five queries regardless of batch size. Messages with no
    resolvable course and no course-level target (global, organization,
    course_family, user scopes) map to ``None``.
    """
    result: Dict[str, Optional[MessageContext]] = {
        str(m.id): None for m in db_messages
    }
    if not db_messages:
        return result

    if course_by_message is None:
        from .audience import course_ids_for_messages
        course_by_message = course_ids_for_messages(db_messages, db)

    sg_ids = {str(m.submission_group_id) for m in db_messages if m.submission_group_id}
    cg_ids = {str(m.course_group_id) for m in db_messages if m.course_group_id}
    content_ids = {str(m.course_content_id) for m in db_messages if m.course_content_id}
    course_ids = {str(c) for c in course_by_message.values() if c}

    sg_rows: Dict[str, tuple] = {}
    if sg_ids:
        sg_rows = {
            str(row[0]): (row[1], str(row[2]) if row[2] else None)
            for row in db.query(
                SubmissionGroup.id,
                SubmissionGroup.display_name,
                SubmissionGroup.course_content_id,
            ).filter(SubmissionGroup.id.in_(sg_ids)).all()
        }
        # Submission-group messages reach their content through the group.
        content_ids.update(cc_id for _, cc_id in sg_rows.values() if cc_id)

    course_titles: Dict[str, Optional[str]] = {}
    if course_ids:
        course_titles = {
            str(row[0]): row[1]
            for row in db.query(Course.id, Course.title)
            .filter(Course.id.in_(course_ids)).all()
        }

    content_rows: Dict[str, tuple] = {}
    if content_ids:
        content_rows = {
            str(row[0]): (row[1], str(row[2]) if row[2] is not None else None)
            for row in db.query(CourseContent.id, CourseContent.title, CourseContent.path)
            .filter(CourseContent.id.in_(content_ids)).all()
        }

    cg_titles: Dict[str, Optional[str]] = {}
    if cg_ids:
        cg_titles = {
            str(row[0]): row[1]
            for row in db.query(CourseGroup.id, CourseGroup.title)
            .filter(CourseGroup.id.in_(cg_ids)).all()
        }

    members_by_sg: Dict[str, List[MessageContextMember]] = {}
    if sg_ids:
        member_rows = (
            db.query(
                SubmissionGroupMember.submission_group_id,
                CourseMember.id,
                User.id,
                User.given_name,
                User.family_name,
                User.email,
            )
            .join(CourseMember, CourseMember.id == SubmissionGroupMember.course_member_id)
            .join(User, User.id == CourseMember.user_id)
            .filter(SubmissionGroupMember.submission_group_id.in_(sg_ids))
            # Insertion order, so the "first member" naming a group without
            # a display_name matches get_computed_display_name().
            .order_by(SubmissionGroupMember.created_at, SubmissionGroupMember.id)
            .all()
        )
        for sg_id, cm_id, user_id, given_name, family_name, _email in member_rows:
            members_by_sg.setdefault(str(sg_id), []).append(MessageContextMember(
                course_member_id=str(cm_id),
                user_id=str(user_id),
                given_name=given_name,
                family_name=family_name,
            ))
        member_emails = {
            (str(row[0]), str(row[2])): row[5] for row in member_rows
        }
    else:
        member_emails = {}

    for message in db_messages:
        msg_id = str(message.id)
        course_id = course_by_message.get(msg_id)
        sg_id = str(message.submission_group_id) if message.submission_group_id else None
        cg_id = str(message.course_group_id) if message.course_group_id else None
        content_id = str(message.course_content_id) if message.course_content_id else None

        if sg_id and sg_id in sg_rows:
            display_name, sg_content_id = sg_rows[sg_id]
            content_id = content_id or sg_content_id
        else:
            display_name = None

        if not course_id and not sg_id and not cg_id and not content_id:
            continue  # global / organization / course_family / user scope

        members = members_by_sg.get(sg_id, []) if sg_id else []
        if sg_id and not display_name:
            # Mirror SubmissionGroup.get_computed_display_name() without its
            # lazy loads: first member's full name, else their email.
            for member in members:
                full_name = f"{member.given_name or ''} {member.family_name or ''}".strip()
                display_name = full_name or member_emails.get((sg_id, member.user_id))
                break

        content_title, content_path = content_rows.get(content_id, (None, None)) if content_id else (None, None)

        result[msg_id] = MessageContext(
            course_id=str(course_id) if course_id else None,
            course_title=course_titles.get(str(course_id)) if course_id else None,
            course_content_id=content_id,
            course_content_title=content_title,
            course_content_path=content_path,
            course_group_id=cg_id,
            course_group_title=cg_titles.get(cg_id) if cg_id else None,
            submission_group_display_name=display_name,
            submission_group_members=members,
        )

    return result
