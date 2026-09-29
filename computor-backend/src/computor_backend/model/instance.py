"""Deployment-wide (instance) settings.

A single row holding the admission limits an operator has to be able to turn
during a running workshop — which is why they live in the database and not in
the image's environment. Two limits, deliberately separate from the per-template
quota in ``WorkspaceTemplateSettings``:

- ``max_workspace_users`` caps how many DISTINCT users may hold an active
  workspace at once. Soft capacity: it exists because a workspace costs memory
  the host may not have, and a user turned away here can still work locally in
  VS Code. Staff bypass it.
- ``max_concurrent_logins`` caps how many DISTINCT users may be logged in at
  once. Staff bypass it too.

Both are the opposite of ``WorkspaceTemplateSettings.max_running_workspaces``,
which models a HARD external constraint (MATLAB licence seats) and therefore
binds admins as well — exempting them there would just move the failure into
the licence server. Keeping the two apart is the whole point of #351.

NULL means unlimited, matching the per-template quota's convention.

Registration admission (the invite-only pilot) lives here too, for the same
reason — an operator closes or opens sign-up without a redeploy:

- ``registration_mode`` decides whether a first SSO login may create a user at
  all: ``open`` (anyone, the behaviour before this column existed),
  ``invite_only`` (only with a valid unused invite code carried through the
  login), ``closed`` (nobody). Existing users always sign in.
- ``max_registered_users`` is a HARD cap on non-staff users, checked under a
  lock on this row whenever a new user would be created, in every mode.
- ``referral_invites_per_user`` single-use invites each non-staff user gets in
  ``invite_only`` mode, created lazily on first read.
- ``pilot_course_ids`` public courses a newly created user is enrolled in,
  subject to each course's own seat cap.
"""
from sqlalchemy import BigInteger, CheckConstraint, Column, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base, UUIDPkMixin, VersionedMixin, AuditMixin


class InstanceSettings(UUIDPkMixin, VersionedMixin, AuditMixin, Base):
    """Singleton row of deployment-wide admission limits.

    ``singleton`` is a constant-valued column with a unique constraint: the
    cheapest way to make "at most one row" a database fact rather than a
    convention every caller has to remember.
    """

    __tablename__ = 'instance_settings'
    __table_args__ = (
        CheckConstraint('singleton = 1', name='instance_settings_singleton_check'),
        CheckConstraint('max_workspace_users IS NULL OR max_workspace_users >= 0',
                        name='instance_settings_workspace_users_check'),
        CheckConstraint('max_concurrent_logins IS NULL OR max_concurrent_logins >= 0',
                        name='instance_settings_logins_check'),
        CheckConstraint('login_idle_minutes >= 1',
                        name='instance_settings_idle_check'),
        CheckConstraint("registration_mode IN ('open', 'invite_only', 'closed')",
                        name='instance_settings_registration_mode_check'),
        CheckConstraint('max_registered_users IS NULL OR max_registered_users >= 0',
                        name='instance_settings_registered_users_check'),
        CheckConstraint('referral_invites_per_user >= 0',
                        name='instance_settings_referral_invites_check'),
    )

    singleton = Column(Integer, nullable=False, unique=True, server_default=text('1'),
                       default=1)
    # Max distinct users holding a running/starting workspace, across ALL
    # templates. NULL = unlimited; 0 stops non-staff provisioning entirely.
    max_workspace_users = Column(BigInteger)
    # Max distinct users holding a live login seat. NULL = unlimited; 0 locks
    # out every non-staff login.
    max_concurrent_logins = Column(BigInteger)
    # How long a login seat survives the user's last authenticated request.
    # Must stay comfortably above permissions/auth.py:AUTH_CACHE_TTL (900s),
    # which is how often an active client re-authenticates and so how often its
    # seat is refreshed — a window below that would evict users mid-session.
    login_idle_minutes = Column(Integer, nullable=False, server_default=text('30'),
                                default=30)
    # Who may create an account on first login: open | invite_only | closed.
    registration_mode = Column(String(16), nullable=False,
                               server_default=text("'open'"), default='open')
    # Hard cap on non-staff, non-service, non-archived users. NULL = unlimited.
    max_registered_users = Column(BigInteger)
    # Single-use referral invites per non-staff user (invite_only mode only).
    referral_invites_per_user = Column(Integer, nullable=False,
                                       server_default=text('2'), default=2)
    # Public course ids a new user is auto-enrolled in (seat caps still apply).
    pilot_course_ids = Column(JSONB, nullable=False,
                              server_default=text("'[]'::jsonb"), default=list)
