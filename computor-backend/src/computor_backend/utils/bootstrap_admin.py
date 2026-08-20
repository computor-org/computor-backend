"""Recognise the deployment's bootstrap administrator.

``API_ADMIN_EMAIL`` provisions exactly one Keycloak account at startup (see
``business_logic.auth.ensure_keycloak_admin``) so a fresh deployment has someone
who can log in. That identity is infrastructure, not a person: it holds
``_admin``, which bypasses every permission check (``permissions/principal.py``),
so it never needs course membership to administer anything.

What course membership *would* buy it is a git repository and a set of git-server
grants — and those cannot work. Its handle is derived from the email local part,
so ``admin@…`` becomes the Forgejo-reserved ``admin`` and then ``admin1``
(``utils/git_username.py``), while the address itself typically belongs to the
git server's own bootstrap admin (``FORGEJO_ADMIN_EMAIL``). Forgejo refuses to
create a second account for a taken email, so no ``admin1`` ever exists and every
collaborator, team and token grant addressed to it fails.

So git provisioning is skipped for this identity, the same way service accounts
are skipped in ``business_logic.course_member_post_create``. Everything else
about the account is untouched: it can still be a course member, still shows up
on the roster, and still administers the course through ``_admin``. A person who
needs to actually *teach* should use their own account.

Recognition is by a stamp on ``User.properties`` written at SSO login, falling
back to a live comparison against ``API_ADMIN_EMAIL`` so an account that predates
the stamp is recognised on its very first provisioning attempt.
"""
from typing import Any, Optional

BOOTSTRAP_ADMIN_PROP = "bootstrap_admin"


def bootstrap_admin_email() -> Optional[str]:
    """The configured bootstrap admin address, lowercased, or None if unset."""
    from computor_backend.settings import settings

    email = getattr(settings, "API_ADMIN_EMAIL", None)
    return email.strip().lower() if email else None


def is_bootstrap_admin_email(email: Optional[str]) -> bool:
    configured = bootstrap_admin_email()
    return bool(configured and email and email.strip().lower() == configured)


def is_bootstrap_admin(user: Any) -> bool:
    """True for the deployment's bootstrap admin account.

    Trusts the stamp first (it survives a later ``API_ADMIN_EMAIL`` change, which
    would otherwise silently re-enable git provisioning for an identity that has
    none), and falls back to the configured address for accounts stamped before
    this existed.
    """
    if user is None:
        return False
    if (getattr(user, "properties", None) or {}).get(BOOTSTRAP_ADMIN_PROP):
        return True
    return is_bootstrap_admin_email(getattr(user, "email", None))


def stamp_bootstrap_admin(user: Any) -> bool:
    """Mark ``user`` as the bootstrap admin when its email says so.

    Returns True when the stamp was newly written, so the caller knows whether
    anything needs committing. Never removes an existing stamp: the identity is
    the one the deployment was bootstrapped with, regardless of later config.
    """
    if user is None or not is_bootstrap_admin_email(getattr(user, "email", None)):
        return False
    props = user.properties or {}
    if props.get(BOOTSTRAP_ADMIN_PROP):
        return False
    user.properties = {**props, BOOTSTRAP_ADMIN_PROP: True}
    return True


def user_is_bootstrap_admin(user_id: Any, db: Any) -> bool:
    """``is_bootstrap_admin`` for a user id, loading the row."""
    from computor_backend.model.auth import User

    if not user_id:
        return False
    user = db.query(User).filter(User.id == str(user_id)).first()
    return is_bootstrap_admin(user)
