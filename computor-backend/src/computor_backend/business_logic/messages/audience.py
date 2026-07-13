"""Message audience resolution — the inverse of the read filter in
``MessagePermissionHandler``: given a stored Message, who can see it."""
from sqlalchemy.orm import Session

from computor_backend.permissions.roles import TUTOR_AND_ABOVE
from computor_backend.model.message import Message
from computor_backend.model.course import (
    Course,
    CourseContent,
    CourseFamilyMember,
    CourseGroup,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.organization import OrganizationMember
from computor_backend.model.role import UserRole


def get_message_recipient_user_ids(message: Message, db: Session, include_global_admins: bool = True) -> set[str]:
    """Compute the set of user_ids that have read access to ``message``.

    Inverse of ``MessagePermissionHandler.build_query`` — given a stored
    Message row, return everyone who can see it. Used by the WS broadcast
    layer to fan messages out to per-user inbox channels (``user:<id>``).

    Single-target invariant: each message has at most one target column
    set, so the per-scope branches below are mutually exclusive.

    Returns an empty set for global messages (no targets) — the broadcast
    layer publishes those to the dedicated ``global`` channel, which every
    connected client is auto-subscribed to.

    Always includes:
    - the author (so they see their own posts on their inbox)
    - every system admin (admins bypass scope checks; their inbox should
      reflect everything)
    """
    user_ids: set[str] = set()

    if message.author_id:
        user_ids.add(str(message.author_id))

    # Global admins can READ everything (broadcast fan-out wants them in the
    # recipient set), but they are not participants of a course scope, so the
    # @mention audience opts out via include_global_admins=False.
    if include_global_admins:
        admin_rows = db.query(UserRole.user_id).filter(UserRole.role_id == "_admin").all()
        user_ids.update(str(r[0]) for r in admin_rows)

    if message.user_id:
        user_ids.add(str(message.user_id))
        return user_ids

    if message.course_member_id:
        cm = db.query(CourseMember).filter(CourseMember.id == message.course_member_id).first()
        if cm:
            user_ids.add(str(cm.user_id))
            user_ids.update(_elevated_user_ids(db, cm.course_id))
        return user_ids

    if message.submission_group_id:
        sg = db.query(SubmissionGroup).filter(
            SubmissionGroup.id == message.submission_group_id
        ).first()
        if sg:
            member_rows = (
                db.query(CourseMember.user_id)
                .join(
                    SubmissionGroupMember,
                    SubmissionGroupMember.course_member_id == CourseMember.id,
                )
                .filter(SubmissionGroupMember.submission_group_id == sg.id)
                .all()
            )
            user_ids.update(str(r[0]) for r in member_rows)
            user_ids.update(_elevated_user_ids(db, sg.course_id))
        return user_ids

    if message.course_group_id:
        cg = db.query(CourseGroup).filter(CourseGroup.id == message.course_group_id).first()
        if cg:
            member_rows = (
                db.query(CourseMember.user_id)
                .filter(CourseMember.course_group_id == cg.id)
                .all()
            )
            user_ids.update(str(r[0]) for r in member_rows)
            user_ids.update(_elevated_user_ids(db, cg.course_id))
        return user_ids

    if message.course_content_id:
        cc = db.query(CourseContent).filter(
            CourseContent.id == message.course_content_id
        ).first()
        if cc:
            member_rows = (
                db.query(CourseMember.user_id)
                .filter(CourseMember.course_id == cc.course_id)
                .all()
            )
            user_ids.update(str(r[0]) for r in member_rows)
        return user_ids

    if message.course_id:
        member_rows = (
            db.query(CourseMember.user_id)
            .filter(CourseMember.course_id == message.course_id)
            .all()
        )
        user_ids.update(str(r[0]) for r in member_rows)
        return user_ids

    if message.course_family_id:
        member_rows = (
            db.query(CourseMember.user_id)
            .join(Course, Course.id == CourseMember.course_id)
            .filter(Course.course_family_id == message.course_family_id)
            .all()
        )
        user_ids.update(str(r[0]) for r in member_rows)
        scoped_rows = (
            db.query(CourseFamilyMember.user_id)
            .filter(CourseFamilyMember.course_family_id == message.course_family_id)
            .all()
        )
        user_ids.update(str(r[0]) for r in scoped_rows)
        return user_ids

    if message.organization_id:
        member_rows = (
            db.query(CourseMember.user_id)
            .join(Course, Course.id == CourseMember.course_id)
            .filter(Course.organization_id == message.organization_id)
            .all()
        )
        user_ids.update(str(r[0]) for r in member_rows)
        scoped_rows = (
            db.query(OrganizationMember.user_id)
            .filter(OrganizationMember.organization_id == message.organization_id)
            .all()
        )
        user_ids.update(str(r[0]) for r in scoped_rows)
        return user_ids

    # Global — recipient set is "everyone connected", which the broadcast
    # layer handles via the dedicated ``global`` channel. Returning an
    # empty set here avoids fanning out N-thousand publishes per message.
    return set()


def _elevated_user_ids(db: Session, course_id) -> set[str]:
    """User IDs holding ``_tutor`` or higher in ``course_id``."""
    rows = (
        db.query(CourseMember.user_id)
        .filter(
            CourseMember.course_id == course_id,
            CourseMember.course_role_id.in_(TUTOR_AND_ABOVE),
        )
        .all()
    )
    return {str(r[0]) for r in rows}
