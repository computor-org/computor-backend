"""Keep Keycloak's ``computor-mfa-required`` role in step with elevated backend roles (issues#485).

Every human holding ``_admin`` or another elevated global role (see
``auth/mfa.py``) gets the Keycloak realm role ``computor-mfa-required``, which
the browser flow set up by ops/keycloak/setup_mfa.py turns into a mandatory OTP
prompt. A holder without an OTP credential also gets the ``CONFIGURE_TOTP``
required action, so the next sign-in enrols an authenticator. When the last
elevated role goes, the realm role is removed again. A pending
``CONFIGURE_TOTP`` and an enrolled authenticator stay: other policies (the
computor.at mail team) require OTP as well.

Triggers:
* startup: full reconcile, which also prunes the role from former holders;
* after any commit that touched ``user_role`` rows (database.py hook);
* every SSO login of a user who holds an elevated role.

All entry points are no-ops unless ``admin_mfa_enforced()``.
"""

import asyncio
import logging
import threading
from collections.abc import Iterable

from sqlalchemy.orm import Session

from computor_backend.auth.mfa import (
    MFA_REALM_ROLE,
    NON_ELEVATED_GLOBAL_ROLES,
    admin_mfa_enforced,
)

logger = logging.getLogger(__name__)

KEYCLOAK_PROVIDER = "keycloak"
ROLE_DESCRIPTION = (
    "Must sign in with a one-time code (TOTP). Managed by the Computor backend "
    "for holders of _admin and global manager roles; do not assign by hand."
)


def keycloak_targets(
    db: Session, user_ids: Iterable[str] | None = None
) -> tuple[set[str], set[str]]:
    """Keycloak user ids that must hold the role, and the ids considered.

    ``user_ids=None`` considers every user with a Keycloak account; otherwise
    only those users. Service accounts are never required (they authenticate
    with API tokens, not the browser flow).
    """
    from computor_backend.model.auth import Account, User
    from computor_backend.model.role import UserRole

    accounts = (
        db.query(Account.user_id, Account.provider_account_id, User.is_service)
        .join(User, User.id == Account.user_id)
        .filter(Account.provider == KEYCLOAK_PROVIDER)
    )
    if user_ids is not None:
        ids = [str(uid) for uid in user_ids]
        if not ids:
            return set(), set()
        accounts = accounts.filter(Account.user_id.in_(ids))
    accounts = accounts.all()

    holders = {
        str(row[0])
        for row in db.query(UserRole.user_id)
        .filter(~UserRole.role_id.in_(NON_ELEVATED_GLOBAL_ROLES))
        .distinct()
        .all()
    }
    considered = {str(kc_id) for _, kc_id, _ in accounts}
    required = {
        str(kc_id)
        for uid, kc_id, is_service in accounts
        if str(uid) in holders and not is_service
    }
    return required, considered


async def _ensure_role(kc) -> dict:
    response = await kc.admin_request("GET", f"/roles/{MFA_REALM_ROLE}")
    if response.status_code == 404:
        created = await kc.admin_request(
            "POST", "/roles", json={"name": MFA_REALM_ROLE, "description": ROLE_DESCRIPTION}
        )
        if created.status_code not in (201, 409):
            created.raise_for_status()
        response = await kc.admin_request("GET", f"/roles/{MFA_REALM_ROLE}")
    response.raise_for_status()
    return response.json()


async def _role_members(kc) -> set[str]:
    members: set[str] = set()
    first = 0
    while True:
        response = await kc.admin_request(
            "GET", f"/roles/{MFA_REALM_ROLE}/users", params={"first": first, "max": 100}
        )
        response.raise_for_status()
        page = response.json()
        members.update(user["id"] for user in page)
        if len(page) < 100:
            return members
        first += len(page)


async def _has_otp(kc, kc_user_id: str) -> bool:
    response = await kc.admin_request("GET", f"/users/{kc_user_id}/credentials")
    response.raise_for_status()
    return any(credential.get("type") == "otp" for credential in response.json())


async def _set_configure_totp(kc, kc_user_id: str, wanted: bool) -> bool:
    """Add or remove the CONFIGURE_TOTP required action; True if it changed."""
    response = await kc.admin_request("GET", f"/users/{kc_user_id}")
    if response.status_code == 404:
        return False
    response.raise_for_status()
    user = response.json()
    actions = list(user.get("requiredActions") or [])
    if wanted == ("CONFIGURE_TOTP" in actions):
        return False
    user["requiredActions"] = (
        actions + ["CONFIGURE_TOTP"] if wanted else [a for a in actions if a != "CONFIGURE_TOTP"]
    )
    updated = await kc.admin_request("PUT", f"/users/{kc_user_id}", json=user)
    updated.raise_for_status()
    return True


async def apply_keycloak_membership(
    required: set[str],
    prune: bool = False,
    considered: set[str] | None = None,
    kc=None,
) -> dict[str, list]:
    """Make Keycloak's role membership match ``required``.

    With ``prune`` every other direct member loses the role (full reconcile);
    otherwise only members in ``considered`` that are not required do.
    """
    if kc is None:
        from computor_backend.auth.keycloak_admin import KeycloakAdminClient

        kc = KeycloakAdminClient()
    role = await _ensure_role(kc)
    members = await _role_members(kc)
    summary: dict[str, list] = {"granted": [], "revoked": [], "enrolment_requested": []}

    for kc_user_id in sorted(required):
        if kc_user_id not in members:
            response = await kc.admin_request(
                "POST", f"/users/{kc_user_id}/role-mappings/realm", json=[role]
            )
            if response.status_code == 404:
                logger.warning("Admin MFA: Keycloak user %s not found; skipped", kc_user_id)
                continue
            response.raise_for_status()
            summary["granted"].append(kc_user_id)
        if not await _has_otp(kc, kc_user_id):
            if await _set_configure_totp(kc, kc_user_id, True):
                summary["enrolment_requested"].append(kc_user_id)

    candidates = members if prune else (members & (considered or set()))
    for kc_user_id in sorted(candidates - required):
        response = await kc.admin_request(
            "DELETE", f"/users/{kc_user_id}/role-mappings/realm", json=[role]
        )
        if response.status_code != 404:
            response.raise_for_status()
        # A pending CONFIGURE_TOTP is left alone: other policies set it too
        # (computor.at's mail team requires OTP of its members).
        summary["revoked"].append(kc_user_id)

    if any(summary.values()):
        logger.info(
            "Admin MFA sync: %d granted, %d revoked, %d asked to enrol",
            len(summary["granted"]), len(summary["revoked"]), len(summary["enrolment_requested"]),
        )
    return summary


async def reconcile_admin_mfa(user_ids: Iterable[str] | None = None) -> dict[str, list] | None:
    """Sync the given backend users (or everyone, pruning) to Keycloak."""
    if not admin_mfa_enforced():
        return None
    from fastapi.concurrency import run_in_threadpool

    from computor_backend.database import get_db_session

    def _targets():
        with get_db_session() as db:
            return keycloak_targets(db, user_ids)

    required, considered = await run_in_threadpool(_targets)
    if user_ids is not None and not considered:
        return None
    return await apply_keycloak_membership(
        required, prune=user_ids is None, considered=considered
    )


def schedule_admin_mfa_sync(user_ids: Iterable[str]) -> None:
    """Fire-and-forget targeted sync after a role change has committed.

    Runs in its own thread with its own event loop, so it works from the sync
    ``after_commit`` hook whether or not an event loop is running, and never
    delays or fails the write that triggered it.
    """
    ids = sorted({str(uid) for uid in user_ids if uid})
    if not ids or not admin_mfa_enforced():
        return

    def _run():
        try:
            asyncio.run(reconcile_admin_mfa(ids))
        except Exception:
            logger.warning("Admin MFA sync failed for %d user(s)", len(ids), exc_info=True)

    threading.Thread(target=_run, name="admin-mfa-sync", daemon=True).start()


async def sync_on_login(user_id: str) -> None:
    """Login-time catch-up for one elevated user; best-effort, never raises.

    Covers role grants that bypassed the commit hook (bulk updates, other
    processes), so the next sign-in of a new admin enrols an authenticator.
    Users without an elevated role are skipped without touching Keycloak.
    """
    if not admin_mfa_enforced():
        return
    from fastapi.concurrency import run_in_threadpool

    from computor_backend.database import get_db_session
    from computor_backend.model.role import UserRole

    def _holds_elevated() -> bool:
        with get_db_session() as db:
            return db.query(
                db.query(UserRole.user_id)
                .filter(
                    UserRole.user_id == user_id,
                    ~UserRole.role_id.in_(NON_ELEVATED_GLOBAL_ROLES),
                )
                .exists()
            ).scalar()

    try:
        if await run_in_threadpool(_holds_elevated):
            await reconcile_admin_mfa([user_id])
    except Exception:
        logger.warning("Admin MFA login sync failed for user %s", user_id, exc_info=True)
