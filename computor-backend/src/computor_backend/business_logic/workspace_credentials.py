"""Rotating a user's workspace app credential.

The credential every workspace app demands is derived from TOKEN_SECRET, the
user id and a per-user key version (``coder/service.py``). Bumping the version
is the revocation: it changes what the platform derives, so the old secret
stops being issued to anything. Pushing is what makes the revocation *take
effect* on workspaces that already exist — their container baked the old secret
into its environment and the ingress into a Traefik label, and only a rebuild
replaces either.

No permission checks live here. The admin endpoint gates on ``workspace:manage``
and the ban endpoint on ``_user_manager``; both then call in.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from computor_backend.coder.client import CoderClient
from computor_backend.coder.naming import encode_coder_username
from computor_backend.coder.service import (
    current_workspace_app_credentials,
    derive_workspace_app_secret,
    workspace_app_key_version,
)
from computor_backend.model.auth import User
from computor_types.coder import (
    WorkspaceCredentialOutcome,
    WorkspaceCredentialRotationResponse,
)

logger = logging.getLogger(__name__)

# Mirrors business_logic.course_workspaces — a workspace counts as running when
# its last build was a start that reached one of these states.
_ACTIVE_BUILD_STATUSES = {"pending", "starting", "running", "succeeded"}


def bump_workspace_app_key_version(
    db: Session, user_id: str, cache=None
) -> tuple[int, datetime]:
    """Move the user to a new key version and commit.

    Returns ``(new_version, rotated_at)``.

    Derives at the new version FIRST: if TOKEN_SECRET is missing the derivation
    raises and nothing is written, rather than burning a version for which no
    code can compute a secret.

    Written as an UPDATE by id rather than by mutating a User object, because
    UserRepository serves cached rows *detached from the session* — assigning to
    such an instance and committing would silently write nothing.

    Pure database work, so it succeeds with Coder disabled or unreachable, which
    is what makes this a durable revocation rather than a best-effort one.
    """
    uid = str(user_id)
    new_version = workspace_app_key_version(db, uid) + 1
    derive_workspace_app_secret(uid, new_version)

    rotated_at = datetime.now(timezone.utc)
    db.query(User).filter(User.id == uid).update(
        {
            User.workspace_app_key_version: new_version,
            User.workspace_app_key_rotated_at: rotated_at,
        },
        synchronize_session=False,
    )
    db.commit()

    # Evict the cached user row so readers do not report the pre-rotation
    # version. Derivation itself reads the DB directly and is unaffected.
    if cache is not None:
        try:
            cache.delete_by_key(cache.key("user", uid))
        except Exception:  # pragma: no cover - cache must never fail a rotation
            logger.warning(f"Could not evict cached user {uid} after rotation", exc_info=True)

    return new_version, rotated_at


async def push_workspace_app_credential(
    db: Session,
    client: CoderClient,
    user_id: str,
    rotated_at: Optional[datetime] = None,
) -> WorkspaceCredentialRotationResponse:
    """Rebuild the user's RUNNING workspaces under their current credential.

    Stopped ones are reported rather than started: the start path sends the
    current credential on every start (see the workspace start endpoint), so
    they cannot come back answering to a revoked secret, and starting a user's
    workspaces just to re-key them would be a surprising side effect.
    """
    user_id = str(user_id)
    response = WorkspaceCredentialRotationResponse(
        user_id=user_id,
        key_version=workspace_app_key_version(db, user_id),
        rotated_at=rotated_at,
    )

    secret, app_hash = current_workspace_app_credentials(db, user_id)
    username = encode_coder_username(user_id)

    # A failure here is a real Coder problem and propagates: the endpoint turns
    # it into a 503, and the ban path catches it. An owner Coder does not know
    # simply has no workspaces, which the empty-list case below covers.
    workspaces = await client.get_user_workspaces(username)
    if not workspaces:
        # The bump already revoked the credential; nothing holds a copy of the
        # old one, so there is nothing to push.
        logger.info(f"User {user_id} has no workspaces; nothing to push to")
        response.pushed = False
        return response

    overrides = {"workspace_app_secret": secret, "workspace_app_hash": app_hash}

    for workspace in workspaces:
        outcome = WorkspaceCredentialOutcome(workspace_name=workspace.name)
        running = (
            workspace.latest_build_transition == "start"
            and (
                workspace.latest_build_status.value
                if workspace.latest_build_status
                else ""
            )
            in _ACTIVE_BUILD_STATUSES
        )
        if not running:
            outcome.error = "Stopped — it picks up the new credential on its next start."
            response.outcomes.append(outcome)
            response.failed += 1
            continue

        try:
            ok = await client.rebuild_with_params(workspace.id, overrides)
        except Exception as e:
            # One unreachable workspace must not strand the rest.
            logger.warning(f"Could not rebuild workspace {workspace.name}: {e}")
            ok = False
        outcome.success = ok
        if ok:
            response.succeeded += 1
        else:
            outcome.error = outcome.error or "Rebuild failed"
            response.failed += 1
        response.outcomes.append(outcome)

    return response


async def rotate_workspace_app_credential(
    db: Session,
    client: Optional[CoderClient],
    user_id: str,
    cache=None,
) -> WorkspaceCredentialRotationResponse:
    """Revoke the user's app credential and push the replacement.

    ``client`` may be None (Coder disabled): the bump still happens, so the old
    credential is revoked and every future provision and start uses the new one.
    """
    user_id = str(user_id)
    new_version, rotated_at = bump_workspace_app_key_version(db, user_id, cache)
    logger.info(f"Workspace app credential of user {user_id} rotated to v{new_version}")

    if client is None:
        return WorkspaceCredentialRotationResponse(
            user_id=user_id,
            key_version=new_version,
            rotated_at=rotated_at,
            pushed=False,
        )

    return await push_workspace_app_credential(db, client, user_id, rotated_at)
