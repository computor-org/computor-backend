"""Connect a pre-provisioned user to a real (logged-in) user.

Course roster imports (CSV / by-email) create bare ``User`` rows keyed only by
the imported address. When the same person later signs in through Keycloak
with a *different* email, the SSO callback cannot link them and auto-creates a
second user — the imported memberships stay on a row nobody can log into.

``connect_users`` repairs that: it moves everything off the pre-provisioned
row onto the real account and deletes the emptied row, in one transaction.
The direction is fixed — the absorbed (source) user must never have
authenticated, so real login history can never be destroyed.

Ordering constraint worth knowing: the DB trigger from migration
``4327038d4ae3`` forbids a ``student_profile.student_email`` equal to another
living user's email. Profiles that are *re-pointed* keep their email column
untouched (no trigger), but merged profile emails may only be written after
the source user row is deleted — hence the delete-then-update tail below.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from computor_backend.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from computor_backend.model.artifact import (
    SubmissionArtifact,
    SubmissionGrade,
    SubmissionReview,
)
from computor_backend.model.auth import Account, StudentProfile, User
from computor_backend.model.course import (
    Course,
    CourseFamilyMember,
    CourseMember,
    CourseMemberComment,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.model.group import UserGroup
from computor_backend.model.message import Message, MessageMention, MessageRead
from computor_backend.model.message_audit import MessageAuditLog
from computor_backend.model.organization import Organization, OrganizationMember
from computor_backend.model.result import Result
from computor_backend.model.role import UserRole
from computor_backend.business_logic.user_lifecycle import login_evidence
from computor_types.users import (
    UserConnectCourseMove,
    UserConnectProfileMove,
    UserConnectResponse,
)

logger = logging.getLogger(__name__)


def _assert_source_never_logged_in(source_id: str, db: Session) -> None:
    """Refuse unless the source user has never authenticated.

    ``login_evidence`` (user_lifecycle.py) is the shared definition of what
    counts as a login: a builtin account (created only by the SSO login flow),
    an API token, or an accepted consent policy.
    """
    evidence = login_evidence(source_id, db)
    if evidence:
        raise ConflictException(
            detail=f"The user to absorb has already authenticated ({evidence}). "
            "Only users that never logged in can be connected into another account."
        )


def _member_blockers(member: CourseMember, submission_group_ids: List[str], db: Session) -> bool:
    """True if the member carries real work and must not be auto-removed."""
    member_id = str(member.id)
    if db.query(Result).filter(Result.course_member_id == member_id).first():
        return True
    if submission_group_ids and db.query(Result).filter(
        Result.submission_group_id.in_(submission_group_ids)
    ).first():
        return True
    if db.query(SubmissionArtifact).filter(
        SubmissionArtifact.uploaded_by_course_member_id == member_id
    ).first():
        return True
    if submission_group_ids and db.query(SubmissionArtifact).filter(
        SubmissionArtifact.submission_group_id.in_(submission_group_ids)
    ).first():
        return True
    if db.query(SubmissionGrade).filter(
        SubmissionGrade.graded_by_course_member_id == member_id
    ).first():
        return True
    if db.query(SubmissionReview).filter(
        SubmissionReview.reviewer_course_member_id == member_id
    ).first():
        return True
    if submission_group_ids and db.query(Message).filter(
        Message.submission_group_id.in_(submission_group_ids)
    ).first():
        return True
    return False


def _submission_group_ids_of(member_id: str, db: Session) -> List[str]:
    rows = (
        db.query(SubmissionGroupMember.submission_group_id)
        .filter(SubmissionGroupMember.course_member_id == member_id)
        .all()
    )
    return [str(r[0]) for r in rows]


def connect_users(
    target_user_id: str,
    source_user_id: str,
    dry_run: bool,
    db: Session,
) -> UserConnectResponse:
    """Absorb ``source_user_id`` (pre-provisioned, never logged in) into ``target_user_id``.

    Re-points course memberships, student profiles, roles, groups,
    organization/family memberships, linked accounts and inbound messages to
    the target, resolves duplicate memberships in favour of the target when
    the source side is an empty shell, then deletes the source user. The
    caller owns the permission check; the commit happens here (never for a
    dry run).
    """
    target_user_id = str(target_user_id)
    source_user_id = str(source_user_id)

    if target_user_id == source_user_id:
        raise BadRequestException(detail="A user cannot be connected to itself")

    target = db.query(User).filter(User.id == target_user_id).first()
    if target is None:
        raise NotFoundException(detail="Target user not found")
    source = db.query(User).filter(User.id == source_user_id).first()
    if source is None:
        raise NotFoundException(detail="Source user not found")

    if target.is_service or source.is_service:
        raise BadRequestException(detail="Service accounts cannot be connected")
    if db.query(UserRole).filter(
        UserRole.user_id == source_user_id, UserRole.role_id == "_admin"
    ).first():
        raise ConflictException(detail="The user to absorb holds the _admin role and cannot be connected")

    _assert_source_never_logged_in(source_user_id, db)

    source_email = source.email

    # ---- Plan: course memberships -------------------------------------------------
    source_members = db.query(CourseMember).filter(CourseMember.user_id == source_user_id).all()
    target_members = db.query(CourseMember).filter(CourseMember.user_id == target_user_id).all()
    target_member_by_course: Dict[str, CourseMember] = {
        str(m.course_id): m for m in target_members
    }

    course_titles: Dict[str, Optional[str]] = {}
    course_ids = {str(m.course_id) for m in source_members} | set(target_member_by_course)
    if course_ids:
        for cid, title in db.query(Course.id, Course.title).filter(Course.id.in_(list(course_ids))):
            course_titles[str(cid)] = title

    membership_moves: List[UserConnectCourseMove] = []
    # (source_member, target_member, submission_group_ids, carries_group)
    duplicates: List[Tuple[CourseMember, CourseMember, List[str], bool]] = []
    blocked_courses: List[str] = []

    for sm in source_members:
        cid = str(sm.course_id)
        tm = target_member_by_course.get(cid)
        if tm is None:
            membership_moves.append(
                UserConnectCourseMove(course_id=cid, course_title=course_titles.get(cid), action="moved")
            )
            continue
        sg_ids = _submission_group_ids_of(str(sm.id), db)
        if _member_blockers(sm, sg_ids, db):
            blocked_courses.append(course_titles.get(cid) or cid)
            continue
        carries_group = tm.course_group_id is None and sm.course_group_id is not None
        duplicates.append((sm, tm, sg_ids, carries_group))
        membership_moves.append(
            UserConnectCourseMove(
                course_id=cid,
                course_title=course_titles.get(cid),
                action="duplicate_removed",
                group_carried_over=carries_group,
            )
        )

    if blocked_courses:
        raise ConflictException(
            detail="Both users are enrolled in "
            + ", ".join(f"'{c}'" for c in blocked_courses)
            + " and the pre-provisioned membership carries results or submissions. "
            "Resolve those memberships manually before connecting the users."
        )

    # ---- Plan: student profiles ---------------------------------------------------
    source_profiles = db.query(StudentProfile).filter(StudentProfile.user_id == source_user_id).all()
    target_profiles = db.query(StudentProfile).filter(StudentProfile.user_id == target_user_id).all()
    target_profile_by_org: Dict[str, StudentProfile] = {
        str(p.organization_id): p for p in target_profiles
    }

    org_titles: Dict[str, Optional[str]] = {}
    org_ids = [str(p.organization_id) for p in source_profiles]
    if org_ids:
        for oid, title in db.query(Organization.id, Organization.title).filter(Organization.id.in_(org_ids)):
            org_titles[str(oid)] = title

    profile_moves: List[UserConnectProfileMove] = []
    # (organization_id, student_email, student_id) to merge onto the target's
    # existing profile — writable only after the source user row is gone.
    merged_profile_fields: List[Tuple[str, Optional[str], Optional[str]]] = []

    for sp in source_profiles:
        oid = str(sp.organization_id)
        merged_email = sp.student_email or source_email
        if oid in target_profile_by_org:
            merged_profile_fields.append((oid, merged_email, sp.student_id))
            profile_moves.append(
                UserConnectProfileMove(
                    organization_id=oid,
                    organization_title=org_titles.get(oid),
                    student_email=merged_email,
                    action="merged",
                )
            )
        else:
            profile_moves.append(
                UserConnectProfileMove(
                    organization_id=oid,
                    organization_title=org_titles.get(oid),
                    student_email=merged_email,
                    action="moved",
                )
            )

    # ---- Plan: roles, groups, org/family memberships, accounts, messages ----------
    target_role_ids = {r.role_id for r in db.query(UserRole).filter(UserRole.user_id == target_user_id)}
    roles_merged = [
        r.role_id
        for r in db.query(UserRole).filter(UserRole.user_id == source_user_id)
        if r.role_id not in target_role_ids
    ]

    source_accounts = db.query(Account).filter(Account.user_id == source_user_id).all()
    target_account_pairs = {
        (a.provider, a.type)
        for a in db.query(Account).filter(Account.user_id == target_user_id)
    }
    account_conflicts = [a for a in source_accounts if (a.provider, a.type) in target_account_pairs]
    if account_conflicts:
        raise ConflictException(
            detail="Both users have a linked account for "
            + ", ".join(f"{a.provider}/{a.type}" for a in account_conflicts)
            + ". Unlink one of them before connecting the users."
        )

    messages_repointed = (
        db.query(Message).filter(Message.user_id == source_user_id).count()
        + db.query(MessageMention).filter(MessageMention.mentioned_user_id == source_user_id).count()
    )

    response = UserConnectResponse(
        dry_run=dry_run,
        source_user_id=source_user_id,
        target_user_id=target_user_id,
        source_email=source_email,
        course_memberships=membership_moves,
        student_profiles=profile_moves,
        roles_merged=roles_merged,
        accounts_moved=len(source_accounts),
        messages_repointed=messages_repointed,
        source_deleted=False,
    )

    if dry_run:
        db.rollback()
        return response

    # ---- Execute ------------------------------------------------------------------
    # 1. Duplicate memberships: keep the target's, salvage what the source's has,
    #    then remove the empty shell (its RESTRICT children first).
    for sm, tm, sg_ids, carries_group in duplicates:
        sm_id = str(sm.id)
        tm_id = str(tm.id)
        if carries_group:
            tm.course_group_id = sm.course_group_id
        db.query(CourseMemberComment).filter(
            CourseMemberComment.course_member_id == sm_id
        ).update({CourseMemberComment.course_member_id: tm_id}, synchronize_session=False)
        db.query(CourseMemberComment).filter(
            CourseMemberComment.transmitter_id == sm_id
        ).update({CourseMemberComment.transmitter_id: tm_id}, synchronize_session=False)
        db.query(Message).filter(Message.course_member_id == sm_id).update(
            {Message.course_member_id: tm_id}, synchronize_session=False
        )

        # The repository row is unique per member; keep the source's only if the
        # target's membership has none (it cascades away with the member otherwise).
        from computor_backend.model.git_server import CourseMemberGitRepository

        target_has_repo = (
            db.query(CourseMemberGitRepository)
            .filter(CourseMemberGitRepository.course_member_id == tm_id)
            .first()
            is not None
        )
        if not target_has_repo:
            db.query(CourseMemberGitRepository).filter(
                CourseMemberGitRepository.course_member_id == sm_id
            ).update({CourseMemberGitRepository.course_member_id: tm_id}, synchronize_session=False)

        db.query(SubmissionGroupMember).filter(
            SubmissionGroupMember.course_member_id == sm_id
        ).delete(synchronize_session=False)
        # Solo groups left without members are import debris; team groups with
        # remaining members stay.
        for sg_id in sg_ids:
            remaining = (
                db.query(SubmissionGroupMember)
                .filter(SubmissionGroupMember.submission_group_id == sg_id)
                .first()
            )
            if remaining is None:
                db.query(SubmissionGroup).filter(SubmissionGroup.id == sg_id).delete(
                    synchronize_session=False
                )
        db.query(CourseMember).filter(CourseMember.id == sm_id).delete(synchronize_session=False)

    # 2. Remaining memberships move wholesale; their submission groups, results
    #    and repository rows hang off course_member.id and follow untouched.
    db.query(CourseMember).filter(CourseMember.user_id == source_user_id).update(
        {CourseMember.user_id: target_user_id}, synchronize_session=False
    )

    # 3. Student profiles: overlapping orgs merge (field copy deferred until the
    #    source row is deleted, see module docstring); the rest re-point, their
    #    student_email column untouched so the uniqueness trigger stays silent.
    merged_org_ids = [oid for oid, _, _ in merged_profile_fields]
    if merged_org_ids:
        db.query(StudentProfile).filter(
            StudentProfile.user_id == source_user_id,
            StudentProfile.organization_id.in_(merged_org_ids),
        ).delete(synchronize_session=False)
    db.query(StudentProfile).filter(StudentProfile.user_id == source_user_id).update(
        {StudentProfile.user_id: target_user_id}, synchronize_session=False
    )

    # 4. Roles and groups: move what the target lacks, drop the rest.
    if roles_merged:
        db.query(UserRole).filter(
            UserRole.user_id == source_user_id, UserRole.role_id.in_(roles_merged)
        ).update({UserRole.user_id: target_user_id}, synchronize_session=False)
    db.query(UserRole).filter(UserRole.user_id == source_user_id).delete(synchronize_session=False)

    target_group_ids = {g.group_id for g in db.query(UserGroup).filter(UserGroup.user_id == target_user_id)}
    source_group_rows = db.query(UserGroup).filter(UserGroup.user_id == source_user_id).all()
    movable_groups = [g.group_id for g in source_group_rows if g.group_id not in target_group_ids]
    if movable_groups:
        db.query(UserGroup).filter(
            UserGroup.user_id == source_user_id, UserGroup.group_id.in_(movable_groups)
        ).update({UserGroup.user_id: target_user_id}, synchronize_session=False)
    db.query(UserGroup).filter(UserGroup.user_id == source_user_id).delete(synchronize_session=False)

    # 5. Organization / course-family memberships, same dedup pattern.
    target_org_ids = {
        str(m.organization_id)
        for m in db.query(OrganizationMember).filter(OrganizationMember.user_id == target_user_id)
    }
    for om in db.query(OrganizationMember).filter(OrganizationMember.user_id == source_user_id).all():
        if str(om.organization_id) in target_org_ids:
            db.query(OrganizationMember).filter(OrganizationMember.id == str(om.id)).delete(
                synchronize_session=False
            )
        else:
            db.query(OrganizationMember).filter(OrganizationMember.id == str(om.id)).update(
                {OrganizationMember.user_id: target_user_id}, synchronize_session=False
            )

    target_family_ids = {
        str(m.course_family_id)
        for m in db.query(CourseFamilyMember).filter(CourseFamilyMember.user_id == target_user_id)
    }
    for fm in db.query(CourseFamilyMember).filter(CourseFamilyMember.user_id == source_user_id).all():
        if str(fm.course_family_id) in target_family_ids:
            db.query(CourseFamilyMember).filter(CourseFamilyMember.id == str(fm.id)).delete(
                synchronize_session=False
            )
        else:
            db.query(CourseFamilyMember).filter(CourseFamilyMember.id == str(fm.id)).update(
                {CourseFamilyMember.user_id: target_user_id}, synchronize_session=False
            )

    # 6. Manually linked (non-builtin) accounts — conflicts were rejected above.
    db.query(Account).filter(Account.user_id == source_user_id).update(
        {Account.user_id: target_user_id}, synchronize_session=False
    )

    # 7. Messages: inbound targets and mentions follow the person; reads and the
    #    audit trail move too so nothing is silently cascaded away.
    db.query(Message).filter(Message.user_id == source_user_id).update(
        {Message.user_id: target_user_id}, synchronize_session=False
    )
    db.query(Message).filter(Message.author_id == source_user_id).update(
        {Message.author_id: target_user_id}, synchronize_session=False
    )
    already_mentioned = [
        str(m.message_id)
        for m in db.query(MessageMention).filter(MessageMention.mentioned_user_id == target_user_id)
    ]
    mention_query = db.query(MessageMention).filter(MessageMention.mentioned_user_id == source_user_id)
    if already_mentioned:
        mention_query.filter(MessageMention.message_id.in_(already_mentioned)).delete(
            synchronize_session=False
        )
        mention_query = db.query(MessageMention).filter(
            MessageMention.mentioned_user_id == source_user_id
        )
    mention_query.update({MessageMention.mentioned_user_id: target_user_id}, synchronize_session=False)

    already_read = [
        str(r.message_id)
        for r in db.query(MessageRead).filter(MessageRead.reader_user_id == target_user_id)
    ]
    read_query = db.query(MessageRead).filter(MessageRead.reader_user_id == source_user_id)
    if already_read:
        read_query.filter(MessageRead.message_id.in_(already_read)).delete(synchronize_session=False)
        read_query = db.query(MessageRead).filter(MessageRead.reader_user_id == source_user_id)
    read_query.update({MessageRead.reader_user_id: target_user_id}, synchronize_session=False)

    db.query(MessageAuditLog).filter(MessageAuditLog.user_id == source_user_id).update(
        {MessageAuditLog.user_id: target_user_id}, synchronize_session=False
    )

    # 8. Delete the emptied source row. Its remaining cascades (profile row,
    #    personal organization) are intentional cleanup; audit columns SET NULL.
    db.query(User).filter(User.id == source_user_id).delete(synchronize_session=False)
    db.flush()

    # 9. Only now may merged profile emails be written (uniqueness trigger).
    for oid, student_email, student_id in merged_profile_fields:
        tp = target_profile_by_org[oid]
        if student_email:
            tp.student_email = student_email
        if student_id and not tp.student_id:
            tp.student_id = student_id
    # Moved profiles created before the import backfilled emails may lack one.
    if source_email:
        db.query(StudentProfile).filter(
            StudentProfile.user_id == target_user_id,
            StudentProfile.student_email.is_(None),
        ).update({StudentProfile.student_email: source_email}, synchronize_session=False)

    # Traceability: record the absorbed identity on the keeper.
    props = dict(target.properties or {})
    connected = list(props.get("connected_users") or [])
    connected.append(
        {
            "user_id": source_user_id,
            "email": source_email,
            "connected_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    props["connected_users"] = connected
    target.properties = props

    db.commit()
    db.expire_all()

    # The membership moves above are bulk ``query(...).update()`` writes, which
    # bypass the ORM flush events that normally stamp affected users stale
    # (database.py, #384) — invalidate the keeper explicitly so a logged-in
    # target sees the absorbed memberships without a re-login.
    from computor_backend.permissions.principal_invalidation import (
        invalidate_user_principals,
    )

    invalidate_user_principals([target_user_id])

    logger.info(
        "Connected pre-provisioned user %s (%s) into %s: %d membership(s), %d profile(s), %d role(s)",
        source_user_id,
        source_email,
        target_user_id,
        len(membership_moves),
        len(profile_moves),
        len(roles_merged),
    )

    response.source_deleted = True
    return response
