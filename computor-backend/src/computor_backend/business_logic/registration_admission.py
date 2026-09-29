"""Who may create a Computor account on first sign-in (invite-only pilot).

The single choke point is the first SSO login in ``business_logic/auth.py``:
whether the person arrived through GitHub brokered by Keycloak or through
Keycloak's own email+password registration form, a new Computor ``User`` is only
ever created there (plus the password-invite accept flow, which checks the same
capacity). ``admit_new_user`` runs inside that transaction, before the insert:

1. ``SELECT ... FOR UPDATE`` on the ``instance_settings`` singleton. Every
   admission serialises on this one row, so "count, then insert" cannot be
   interleaved by a second login taking the last seat.
2. ``closed`` refuses. The email must be verified by the IdP whenever the mode
   is not ``open``.
3. ``max_registered_users`` (hard, every mode) counts non-staff users.
4. ``invite_only`` requires an invite code, consumed with a single conditional
   ``UPDATE ... WHERE use_count < max_uses ... RETURNING`` — so the same code
   can never admit two people, whatever the interleaving.

A refusal raises ``RegistrationRefused``; the caller rolls back (nothing was
written, the invite is not spent) and sends the browser to a page explaining
why. Existing users never reach this module.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import exists, func, select, text, update
from sqlalchemy.orm import Session

from computor_backend.business_logic.instance_limits import STAFF_BYPASS_ROLES
from computor_backend.exceptions import ForbiddenException
from computor_backend.model.auth import User
from computor_backend.model.instance import InstanceSettings
from computor_backend.model.invite import InviteLink
from computor_backend.model.role import UserRole

logger = logging.getLogger(__name__)

REGISTRATION_MODES = ("open", "invite_only", "closed")

# How long a lazily created referral invite stays valid.
REFERRAL_INVITE_DAYS = 365

# Refusal reasons, also the ``reason`` the web page at /join/refused renders.
REASON_CLOSED = "closed"
REASON_FULL = "full"
REASON_INVITE_REQUIRED = "invite_required"
REASON_INVITE_INVALID = "invite_invalid"
REASON_EMAIL_UNVERIFIED = "email_unverified"

_MESSAGES = {
    REASON_CLOSED: "Registration is closed on this Computor instance.",
    REASON_FULL: "The pilot is full: no new accounts can be created right now.",
    REASON_INVITE_REQUIRED: "Registration is by invitation only. "
    "Open the invite link you were given and sign in from there.",
    REASON_INVITE_INVALID: "This invite link is invalid, already used, or expired.",
    REASON_EMAIL_UNVERIFIED: "Please verify your email address first, "
    "then sign in again (from your invite link, if you have one).",
}


class RegistrationRefused(ForbiddenException):
    """A first login that may not create a user. Nothing has been written.

    The Keycloak account behind the attempt is left alone: the login path only
    ends the browser's Keycloak session. Deleting it was unsafe — nothing
    proves this attempt created it (a concurrent first login of the same
    identity, or a long-standing Keycloak account without a Computor row).
    """

    def __init__(self, reason: str):
        super().__init__(
            error_code="AUTHZ_001",
            detail=_MESSAGES[reason],
            context={"registration_refused": reason},
        )
        self.reason = reason
        # Filled in by the login path for the Keycloak logout redirect.
        self.id_token: Optional[str] = None


def lock_first_login(db: Session, provider: str, subject: str, email: Optional[str]) -> None:
    """Serialise first logins per identity and per email for this transaction.

    Two first logins of the same identity (a double-clicked callback, two
    tabs) would otherwise both miss the account lookup and race to create
    it. Taken before the lookups, which the caller must (re)do afterwards.
    Always identity first, then email, so two transactions never wait on each
    other in a cycle. Transaction-scoped advisory locks: released on commit
    or rollback. PostgreSQL only; a no-op elsewhere.
    """
    if db.get_bind().dialect.name != "postgresql":
        return
    keys = [f"first_login:{provider}:{subject}"]
    if email:
        keys.append(f"first_login_email:{email.lower()}")
    for key in keys:
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": key}
        )


def _staff_user_ids():
    return select(UserRole.user_id).where(UserRole.role_id.in_(STAFF_BYPASS_ROLES))


def count_registered_users(db: Session) -> int:
    """Users that count against ``max_registered_users``.

    Excludes service accounts, archived users (archiving frees a seat), and
    holders of a staff role — the operators must never be counted out of
    their own instance.
    """
    return int(
        db.query(func.count(User.id))
        .filter(
            User.is_service.is_(False),
            User.archived_at.is_(None),
            ~User.id.in_(_staff_user_ids()),
        )
        .scalar()
        or 0
    )


def lock_instance_settings(db: Session) -> Optional[InstanceSettings]:
    """The settings row, locked for the rest of the transaction (or None)."""
    return db.query(InstanceSettings).with_for_update().first()


def check_registration_capacity(db: Session) -> Optional[InstanceSettings]:
    """Lock the settings row and refuse if a new non-staff user may not exist.

    Covers mode ``closed`` and the hard user cap; the caller decides about
    invites. Returns the (locked) row, or None when no settings exist
    (registration open and unlimited, the pre-pilot behaviour).
    """
    row = lock_instance_settings(db)
    if row is None:
        return None
    if row.registration_mode == "closed":
        raise RegistrationRefused(REASON_CLOSED)
    cap = row.max_registered_users
    if cap is not None and count_registered_users(db) >= cap:
        raise RegistrationRefused(REASON_FULL)
    return row


def consume_invite(db: Session, code: str, email: Optional[str]) -> Optional[Tuple[str, Optional[str]]]:
    """Spend one use of ``code`` atomically; ``(invite_id, created_by)`` or None.

    One conditional UPDATE: under READ COMMITTED a second transaction racing
    for the same code blocks on the row, then re-evaluates the WHERE against
    the committed ``use_count`` — so it cannot also succeed.
    """
    now = datetime.now(timezone.utc)
    conditions = [
        InviteLink.token == code,
        InviteLink.revoked_at.is_(None),
        InviteLink.expires_at > now,
        InviteLink.use_count < InviteLink.max_uses,
    ]
    if email:
        conditions.append(
            (InviteLink.email.is_(None)) | (func.lower(InviteLink.email) == email.lower())
        )
    else:
        conditions.append(InviteLink.email.is_(None))
    row = db.execute(
        update(InviteLink)
        .where(*conditions)
        .values(use_count=InviteLink.use_count + 1, updated_at=now)
        .returning(InviteLink.id, InviteLink.created_by)
        .execution_options(synchronize_session=False)
    ).first()
    if row is None:
        return None
    return str(row[0]), (str(row[1]) if row[1] is not None else None)


def refund_invite(db: Session, invite_id: str) -> None:
    """Give back one use spent by ``consume_invite`` whose admission failed."""
    db.execute(
        update(InviteLink)
        .where(InviteLink.id == invite_id, InviteLink.use_count > 0)
        .values(use_count=InviteLink.use_count - 1)
        .execution_options(synchronize_session=False)
    )


def admit_new_user(
    db: Session,
    *,
    invite_code: Optional[str],
    email: Optional[str],
    email_verified: bool,
    is_staff: bool = False,
) -> Optional[Tuple[str, Optional[str]]]:
    """Gate the creation of a brand-new user; returns the consumed invite.

    Must run in the transaction that inserts the user, which must commit (or
    roll back) promptly: the settings row stays locked until then. Staff (a
    Keycloak ``administrators`` member) are never refused.
    """
    if is_staff:
        return None
    row = lock_instance_settings(db)
    mode = row.registration_mode if row is not None else "open"
    # handle_sso_callback already refuses an unverified email in every mode
    # before getting here; this still covers identities that carry no email.
    if mode != "open" and not email_verified:
        raise RegistrationRefused(REASON_EMAIL_UNVERIFIED)
    check_registration_capacity(db)

    code = (invite_code or "").strip() or None
    if mode == "invite_only" and code is None:
        raise RegistrationRefused(REASON_INVITE_REQUIRED)
    consumed = consume_invite(db, code, email) if code else None
    if mode == "invite_only" and consumed is None:
        raise RegistrationRefused(REASON_INVITE_INVALID)
    # In ``open`` mode a code is optional: spent if valid (for the referral
    # record), ignored if not.
    return consumed


def record_invite(user: User, consumed: Optional[Tuple[str, Optional[str]]]) -> None:
    """Remember which invite (and so which referrer) admitted ``user``."""
    if consumed is None:
        return
    user.registered_via_invite_id, user.referred_by_user_id = consumed


def invite_public_status(invite: Optional[InviteLink]) -> str:
    """valid | used | expired | invalid — nothing about who issued it."""
    if invite is None or invite.revoked_at is not None:
        return "invalid"
    exp = invite.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp <= datetime.now(timezone.utc):
        return "expired"
    if invite.use_count >= invite.max_uses:
        return "used"
    return "valid"


def ensure_referral_invites(db: Session, user_id: str) -> List[InviteLink]:
    """The user's referral invites, topped up to the configured count.

    Created only in ``invite_only`` mode (elsewhere they would be dead
    weight); existing ones are always returned. Used invites count towards
    the allowance — it is a lifetime number, not a refill. The user row is
    locked so two concurrent reads cannot both top up.
    """
    row = db.query(InstanceSettings).first()
    db.query(User.id).filter(User.id == user_id).with_for_update().first()

    def _existing() -> List[InviteLink]:
        return (
            db.query(InviteLink)
            .filter(InviteLink.created_by == user_id, InviteLink.kind == "referral")
            .order_by(InviteLink.created_at, InviteLink.id)
            .all()
        )

    invites = _existing()
    if row is not None and row.registration_mode == "invite_only":
        missing = int(row.referral_invites_per_user or 0) - len(invites)
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFERRAL_INVITE_DAYS)
        for _ in range(max(missing, 0)):
            invite = InviteLink(
                token=InviteLink.generate_token(),
                created_by=user_id,
                max_uses=1,
                use_count=0,
                expires_at=expires_at,
                roles=[],
                note="referral",
                kind="referral",
            )
            db.add(invite)
        if missing > 0:
            db.flush()
            invites = _existing()  # same order as every later read
    db.commit()
    return invites


def user_is_staff(db: Session, user_id: str) -> bool:
    return bool(
        db.query(
            exists().where(
                UserRole.user_id == user_id, UserRole.role_id.in_(STAFF_BYPASS_ROLES)
            )
        ).scalar()
    )


async def enroll_in_pilot_courses(db: Session, user_id: str) -> List[str]:
    """Enrol a just-created user in the configured pilot courses.

    Best effort, after the user is committed: a full or no-longer-public course
    is logged and skipped, never a reason to fail the sign-in. Goes through the
    ordinary self-registration path, so each course's seat cap still binds.
    Returns the ids of the courses the user is now a member of.
    """
    row = db.query(InstanceSettings).first()
    course_ids = list(row.pilot_course_ids or []) if row is not None else []
    if not course_ids:
        return []

    from computor_backend.business_logic.course_registration import (
        register_in_public_course,
    )
    from computor_backend.permissions.principal import Principal

    enrolled = []
    for course_id in course_ids:
        try:
            await register_in_public_course(course_id, Principal(user_id=user_id), db)
            enrolled.append(str(course_id))
        except Exception as exc:  # noqa: BLE001 - one course must not block the rest
            db.rollback()
            logger.warning(f"Pilot enrolment of {user_id} in {course_id} skipped: {exc}")
    return enrolled
