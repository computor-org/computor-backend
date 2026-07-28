"""
Business logic for Coder workspace management.

This module provides service functions for workspace operations that
require access to backend repositories and utilities.
"""

import base64
import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from computor_backend.model.service import ApiToken
from computor_backend.repositories import ApiTokenRepository, UserRepository
from computor_backend.utils.api_token import generate_api_token
from computor_backend.utils.encryption import _token_secret

logger = logging.getLogger(__name__)


# Domain separator, so this secret can never collide with another HMAC derived
# from the same TOKEN_SECRET.
_APP_SECRET_CONTEXT = b"computor:workspace-app-auth:v1"


def derive_workspace_app_secret(user_id: str, key_version: int = 1) -> str:
    """Credential the workspace apps require and the ingress injects.

    Workspace apps (ttyd, KasmVNC, Jupyter, code-server) bind on 0.0.0.0 and
    all workspaces share a Docker bridge, so without a credential any workspace
    can drive any other one directly by container name, never touching the
    proxy that does the authentication. Requiring this secret closes that.

    Per USER rather than per workspace: /home/coder is one volume shared across
    all of a user's workspaces, so a per-workspace secret would make two of
    their running desktops fight over ~/.kasmpasswd. Sharing it between a
    single user's own workspaces is not a weakening — they are the same trust
    domain — while a different user still cannot authenticate.

    ``key_version`` (``user.workspace_app_key_version``) makes the credential
    revocable for ONE user: bumping it yields a different secret, and pushing
    that onto their workspaces invalidates the old one. Version 1 is the
    original derivation, so nothing already provisioned changes value.

    Derived rather than stored *by Computor*: deterministic from TOKEN_SECRET,
    so we hold no secret and a rebuild reproduces the value. It is NOT absent
    at rest generally — Coder persists both this and its argon2 hash as rich
    build parameters, and the hash also sits in a Traefik label, where it is a
    bearer equivalent (see ``workspace_app_password_hash``). Anyone who can
    read those can authenticate; the key version is what makes that
    recoverable.
    """
    message = _APP_SECRET_CONTEXT + str(user_id).encode("utf-8")
    if key_version and int(key_version) > 1:
        # Appended only from v2 so v1 stays byte-identical to the original
        # derivation. A UUID cannot contain ':', so the suffix is unambiguous.
        message += b":" + str(int(key_version)).encode("ascii")
    digest = hmac.new(
        _token_secret().encode("utf-8"),
        message,
        hashlib.sha256,
    ).digest()
    # URL-safe and free of ':' so it survives basic-auth and token headers.
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def workspace_app_password_hash(secret: str) -> str:
    """Argon2id hash of the app secret, for the code-server templates.

    code-server keeps its session in a `code-server-session` cookie holding an
    argon2 hash; with HASHED_PASSWORD set it compares the cookie against that
    hash directly. Handing the template both values lets the ingress inject a
    ready-made session cookie, so a user never sees a login page.

    Note what that comparison implies: code-server checks the cookie for
    EQUALITY with the hash, it does not verify the secret against it. So this
    hash is a bearer credential, not a one-way digest — whoever reads it (the
    Traefik label, Coder's build parameters) can mint a session without ever
    knowing the secret. Argon2's cost parameters buy nothing here; treat the
    hash exactly as carefully as the secret.

    Salted, so each call returns a different string: the value that reaches the
    container and the value the ingress injects must come from the same build.
    """
    from argon2 import PasswordHasher

    return PasswordHasher().hash(secret)


def workspace_app_key_version(db: Session, user_id: str) -> int:
    """The user's current app-credential key version.

    Read straight from the database rather than through UserRepository: user
    rows are Redis-cached for an hour, and a stale version here would keep
    re-issuing a credential that was just revoked.
    """
    from computor_backend.model.auth import User

    version = (
        db.query(User.workspace_app_key_version)
        .filter(User.id == str(user_id))
        .scalar()
    )
    return int(version or 1)


def current_workspace_app_credentials(db: Session, user_id: str) -> tuple[str, str]:
    """``(secret, argon2 hash)`` at the user's current key version."""
    secret = derive_workspace_app_secret(user_id, workspace_app_key_version(db, user_id))
    return secret, workspace_app_password_hash(secret)


def workspace_app_credentials_for_owner(
    db: Session, owner_name: Optional[str]
) -> Optional[tuple[str, str]]:
    """Current credentials for a Coder workspace owner, or None.

    None when the owner has no Computor user behind it — Coder's own ``admin``
    account, or a workspace whose user was deleted — and when TOKEN_SECRET is
    unavailable. Callers carry the previous build's values forward in that
    case rather than issuing something nobody can reproduce.
    """
    from computor_backend.coder.naming import decode_coder_username
    from computor_backend.model.auth import User

    user_id = decode_coder_username(owner_name)
    if user_id is None:
        return None
    exists = db.query(User.id).filter(User.id == user_id).scalar()
    if exists is None:
        logger.info(f"Coder owner '{owner_name}' has no Computor user; carrying credentials")
        return None
    try:
        return current_workspace_app_credentials(db, user_id)
    except Exception as e:
        logger.warning(f"Could not derive app credentials for '{owner_name}': {e}")
        return None


def mint_workspace_token(
    db: Session,
    cache,
    target_user_id: str,
    created_by: str,
    workspace_name: str,
    ttl_days: Optional[int] = 30,
) -> Optional[str]:
    """
    Mint an API token for workspace auto-login.

    This creates a per-workspace singleton token named
    "workspace-auto-login:{workspace_name}". If a token with this name already
    exists, it is revoked first (rotation), so each provision hands THAT
    workspace a fresh token and invalidates its old one — tokens of the user's
    other workspaces stay valid.

    The token is given a bounded lifetime (``ttl_days``) so a leaked
    COMPUTOR_AUTH_TOKEN cannot be used indefinitely; an actively-used workspace
    is re-provisioned (and thus re-minted) well within that window.

    Args:
        db: Database session
        cache: Redis cache instance
        target_user_id: User ID to create the token for
        created_by: User ID of the admin creating the token
        workspace_name: Effective (sanitized) workspace name the token is for
        ttl_days: Token lifetime in days; ``None`` or <= 0 means never expire

    Returns:
        The full token string if successful, None if failed
    """
    logger.info(
        f"mint_workspace_token called: target={target_user_id}, by={created_by}, "
        f"workspace={workspace_name}"
    )
    try:
        token_repo = ApiTokenRepository(db, cache)
        token_name = f"workspace-auto-login:{workspace_name}"

        # Revoke existing tokens with this name (per-workspace singleton)
        existing = token_repo.find_all_active_by_name(target_user_id, token_name)
        # Tokens minted before the per-workspace scheme were named plain
        # "workspace-auto-login" and belonged to the old default workspace
        # ("workspace") — rotate those too when re-provisioning it.
        if workspace_name == "workspace":
            existing = list(existing) + list(
                token_repo.find_all_active_by_name(target_user_id, "workspace-auto-login")
            )
        for old_token in existing:
            token_repo.revoke(str(old_token.id), reason="replaced by new workspace provision")
            logger.info(f"Revoked existing workspace token: {old_token.id}")

        # Generate and create new token
        full_token, token_prefix, token_hash = generate_api_token()
        expires_at = None
        if ttl_days and ttl_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
        api_token = ApiToken(
            name=token_name,
            description="Auto-generated token for VSCode extension in workspace",
            user_id=target_user_id,
            token_hash=token_hash,
            token_prefix=token_prefix,
            scopes=[],
            expires_at=expires_at,
            created_by=created_by,
        )
        db.add(api_token)
        db.commit()

        logger.info(f"Minted workspace token for user {target_user_id} (prefix: {token_prefix}, length: {len(full_token)})")
        return full_token

    except Exception as e:
        logger.error(f"Failed to mint workspace token: {e}", exc_info=True)
        db.rollback()
        return None


def get_user_by_id(db: Session, cache, user_id: str):
    """
    Get a user by ID from the database.

    Args:
        db: Database session
        cache: Redis cache instance
        user_id: User ID to look up

    Returns:
        User object if found

    Raises:
        NotFoundError: If user not found
    """
    user_repo = UserRepository(db, cache)
    return user_repo.get_by_id(user_id)


def get_user_by_email(db: Session, cache, email: str):
    """
    Get a user by email from the database.

    Args:
        db: Database session
        cache: Redis cache instance
        email: Email address to look up

    Returns:
        User object if found, None if not found
    """
    user_repo = UserRepository(db, cache)
    return user_repo.find_by_email(email)


def get_user_email(user) -> str:
    """
    Get user email with fallback to username@computor.local.

    Args:
        user: User object with email and username attributes

    Returns:
        Email string
    """
    return user.email or f"user_{user.id}@computor.local"


def get_user_fullname(user) -> Optional[str]:
    """
    Get user full name if both given and family name are set.

    Args:
        user: User object with given_name and family_name attributes

    Returns:
        Full name string or None
    """
    if user.given_name and user.family_name:
        return f"{user.given_name} {user.family_name}"
    return None
