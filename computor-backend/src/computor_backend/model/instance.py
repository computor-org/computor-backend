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
"""
from sqlalchemy import BigInteger, CheckConstraint, Column, Integer, text

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
