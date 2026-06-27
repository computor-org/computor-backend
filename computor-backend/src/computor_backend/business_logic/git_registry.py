"""Git server registry management.

The registry holds the git server instances Computor knows about (our Forgejo,
external GitLabs). ``managed`` instances carry an encrypted service token used
for backend-babysat student-repo provisioning.

Authorization: admin or ``_organization_manager`` (the global cross-org
manager). The registry stores service credentials, so it is intentionally
restricted. Tokens are write-only — stored encrypted, never returned.
"""
import logging
from typing import List
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from computor_backend.model.git_server import GitServer
from computor_backend.permissions.principal import Principal
from computor_types.git_registry import GitServerCreate, GitServerGet, GitServerUpdate
from computor_types.encryption import encrypt_secret

logger = logging.getLogger(__name__)


def ensure_managed_forgejo_registered() -> None:
    """Idempotently register the configured managed Forgejo as a git server.

    Course creation offers git servers from this registry, but the Forgejo we
    operate — described in the environment (``GIT_SERVER=forgejo``,
    ``GIT_SERVER_URL``, admin user/pass) — is never turned into a registry row,
    so the dropdown would be empty until an admin registered it by hand. This
    seeds that row at startup and mints the service token the backend needs to
    provision course/student repos (a token cannot mint another token, so we use
    the admin's basic-auth credentials once). Best-effort and idempotent: a row
    that already carries a token is left untouched; if Forgejo is unreachable we
    log and leave it for the next startup.
    """
    from computor_backend.database import get_db_session
    from computor_backend.git_server.config import get_git_server_settings
    from computor_backend.git_provider.forgejo import ForgejoProviderClient

    cfg = get_git_server_settings()
    if not (
        cfg.is_forgejo
        and cfg.git_server_url
        and cfg.git_server_admin_username
        and cfg.git_server_admin_password
    ):
        return

    base_url = cfg.git_server_url.rstrip("/")
    with get_db_session() as db:
        server = (
            db.query(GitServer)
            .filter(GitServer.type == "forgejo", GitServer.base_url == base_url)
            .first()
        )
        if server is not None and server.token:
            return  # already registered and usable

        token = ForgejoProviderClient(base_url, "").mint_admin_service_token(
            cfg.git_server_admin_username, cfg.git_server_admin_password
        )
        if not token:
            logger.warning(
                "Managed Forgejo at %s not registered yet — service token mint failed "
                "(Forgejo may still be starting); will retry next startup.",
                base_url,
            )
            return

        if server is None:
            server = GitServer(
                type="forgejo",
                base_url=base_url,
                name="Computor Forgejo",
                managed=True,
                token=encrypt_secret(token),
            )
            db.add(server)
            logger.info("Registered managed Forgejo git server %s", base_url)
        else:
            server.token = encrypt_secret(token)
            server.managed = True
            logger.info("Backfilled service token for managed Forgejo git server %s", base_url)
        db.commit()


def is_registry_admin(principal: Principal) -> bool:
    """Who may manage the git server registry: admins and ``_organization_manager``."""
    return bool(principal.is_admin or "_organization_manager" in (principal.roles or []))


def _require_registry_admin(principal: Principal) -> None:
    if not is_registry_admin(principal):
        raise ForbiddenException(
            "Managing the git server registry requires admin or _organization_manager."
        )


def _to_get(server: GitServer) -> GitServerGet:
    parent_group_id = ((server.properties or {}).get("gitlab") or {}).get("parent_group_id")
    return GitServerGet(
        id=str(server.id),
        type=server.type,
        base_url=server.base_url,
        name=server.name,
        managed=bool(server.managed),
        has_token=bool(server.token),
        parent_group_id=parent_group_id,
        created_at=server.created_at,
    )


def create_git_server(data: GitServerCreate, principal: Principal, db: Session) -> GitServerGet:
    _require_registry_admin(principal)
    server = GitServer(
        type=data.type,
        base_url=data.base_url.rstrip("/"),
        name=data.name,
        managed=data.managed,
        token=encrypt_secret(data.token) if data.token else None,
        created_by=principal.get_user_id(),
    )
    if data.parent_group_id:
        server.properties = {"gitlab": {"parent_group_id": data.parent_group_id}}
    db.add(server)
    db.commit()
    db.refresh(server)
    logger.info(
        "Registered git server %s (%s) managed=%s", server.base_url, server.type, server.managed
    )
    return _to_get(server)


def list_git_servers(principal: Principal, db: Session) -> List[GitServerGet]:
    _require_registry_admin(principal)
    servers = db.query(GitServer).order_by(GitServer.created_at).all()
    return [_to_get(s) for s in servers]


def get_git_server(server_id: UUID | str, principal: Principal, db: Session) -> GitServerGet:
    _require_registry_admin(principal)
    server = db.query(GitServer).filter(GitServer.id == str(server_id)).first()
    if not server:
        raise NotFoundException("Git server not found")
    return _to_get(server)


def update_git_server(
    server_id: UUID | str, data: GitServerUpdate, principal: Principal, db: Session
) -> GitServerGet:
    _require_registry_admin(principal)
    server = db.query(GitServer).filter(GitServer.id == str(server_id)).first()
    if not server:
        raise NotFoundException("Git server not found")

    if data.name is not None:
        server.name = data.name
    if data.managed is not None:
        server.managed = data.managed
    if data.token is not None:
        # "" clears the token; a non-empty value replaces it (re-encrypted).
        server.token = encrypt_secret(data.token) if data.token else None
    if data.parent_group_id is not None:
        # "" clears it; a value sets it. Reassign a fresh dict so the JSONB change
        # is tracked.
        props = dict(server.properties or {})
        gl = dict(props.get("gitlab") or {})
        gl["parent_group_id"] = data.parent_group_id or None
        props["gitlab"] = gl
        server.properties = props
    server.updated_by = principal.get_user_id()

    db.commit()
    db.refresh(server)
    return _to_get(server)


def delete_git_server(server_id: UUID | str, principal: Principal, db: Session) -> None:
    _require_registry_admin(principal)
    server = db.query(GitServer).filter(GitServer.id == str(server_id)).first()
    if not server:
        raise NotFoundException("Git server not found")
    try:
        db.delete(server)
        db.commit()
    except IntegrityError:
        # course_git_binding.git_server_id is ON DELETE RESTRICT.
        db.rollback()
        raise BadRequestException(
            "Git server is still referenced by one or more course bindings; rebind those courses first."
        )
