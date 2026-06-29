"""Idempotent startup seeding of bootstrap services from ``data/deployments/*``.

The default testing worker (and any other system service) needs a ``Service`` +
predefined API token to exist before it can authenticate. Rather than juggle a
``deployment.yaml`` + a matching ``.env`` token by hand, we apply the
``services:`` section of any YAML under the deployments directory on every API
start — created once, then a no-op.

Single source of truth for the token: the YAML uses ``api_token.token:
${TESTING_WORKER_TOKEN}`` and we ``os.path.expandvars`` it, so the value comes
from the same environment variable the ``temporal-worker-testing`` container
passes as ``API_TOKEN``. They can't drift.

Mirrors the style of ``ensure_managed_forgejo_registered`` /
``db_apply_roles``: synchronous, best-effort, logged, never raises into startup.
Only the ``services:`` section is applied here — organizations/users/contents are
out of scope for boot seeding.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import yaml

from computor_types.api_tokens import ApiTokenAdminCreate
from computor_types.deployments_refactored import ComputorDeploymentConfig, ServiceConfig
from computor_types.services import ServiceCreate

from computor_backend.business_logic.api_tokens import create_api_token_admin
from computor_backend.business_logic.service_accounts import create_service_account
from computor_backend.database import get_db_session
from computor_backend.model.service import ApiToken, Service
from computor_backend.permissions.principal import Principal

logger = logging.getLogger(__name__)


def _deployments_dir() -> str:
    """Directory of bootstrap deployment YAMLs.

    Set ``DEPLOYMENTS_DIR`` explicitly (the prod container mounts the staged dir
    there); on the dev host the API runs from the repo root, so the default
    ``data/deployments`` resolves to the repo's directory.
    """
    return os.environ.get("DEPLOYMENTS_DIR") or os.path.join("data", "deployments")


def ensure_bootstrap_services() -> None:
    """Apply the ``services:`` of every ``data/deployments/*.yaml`` idempotently."""
    deployments_dir = _deployments_dir()
    if not os.path.isdir(deployments_dir):
        logger.info("[bootstrap] no deployments dir at %s — skipping", deployments_dir)
        return

    files = sorted(
        f
        for f in os.listdir(deployments_dir)
        if f.endswith((".yaml", ".yml")) and not f.endswith((".example.yaml", ".example.yml"))
    )
    if not files:
        return

    system = Principal(is_admin=True)  # trusted boot context; created_by stays NULL
    with get_db_session() as db:
        for fname in files:
            path = os.path.join(deployments_dir, fname)
            try:
                with open(path, "r") as fh:
                    data = yaml.safe_load(fh) or {}
                config = ComputorDeploymentConfig(**data)
            except Exception as exc:  # noqa: BLE001 - one bad file shouldn't block the rest
                logger.warning("[bootstrap] %s: invalid deployment YAML, skipping: %s", fname, exc)
                continue

            for svc in (config.services or []):
                try:
                    _ensure_service(svc, system, db)
                except Exception as exc:  # noqa: BLE001 - best-effort per service
                    logger.warning(
                        "[bootstrap] service '%s' (%s) failed: %s",
                        getattr(svc, "slug", "?"), fname, exc,
                    )


def _ensure_service(svc: ServiceConfig, system: Principal, db) -> None:
    existing = db.query(Service).filter(Service.slug == svc.slug).first()
    if existing is None:
        created = create_service_account(
            ServiceCreate(
                slug=svc.slug,
                name=(svc.user.given_name or svc.slug.replace("-", " ").replace(".", " ").title()),
                description=svc.description or f"Service for {svc.slug}",
                service_type=svc.service_type_path,
                username=svc.user.username,
                email=svc.user.email,
                given_name=svc.user.given_name,
                family_name=svc.user.family_name,
                config=svc.config or {},
                enabled=True,
            ),
            system,
            db,
        )
        user_id = str(created.user_id)
        logger.info("[bootstrap] created service %s", svc.slug)
    else:
        user_id = str(existing.user_id)

    # Token is idempotent: leave any existing active token untouched (a changed
    # ${TESTING_WORKER_TOKEN} is intentionally NOT auto-rotated here — that would
    # silently break a running worker; rotate it deliberately instead).
    has_token = (
        db.query(ApiToken)
        .filter(ApiToken.user_id == user_id, ApiToken.revoked_at.is_(None))
        .first()
    )
    if has_token is not None:
        return

    raw = svc.api_token.token if svc.api_token else None
    if not raw:
        logger.warning(
            "[bootstrap] service %s has no predefined api_token.token — left without a token",
            svc.slug,
        )
        return

    token = os.path.expandvars(raw)
    if not token or token.startswith("${") or not token.startswith("ctp_") or len(token) < 32:
        logger.warning(
            "[bootstrap] service %s: api_token did not resolve to a valid 'ctp_' token "
            "(is the env var set/exported?) — left without a token",
            svc.slug,
        )
        return

    expires_at = None
    if svc.api_token.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=svc.api_token.expires_days)

    create_api_token_admin(
        ApiTokenAdminCreate(
            name=svc.api_token.name or f"{svc.slug} token",
            description=f"API token for {svc.slug}",
            user_id=user_id,
            predefined_token=token,
            scopes=svc.api_token.scopes or [],
            expires_at=expires_at,
        ),
        system,
        db,
    )
    logger.info("[bootstrap] set predefined token for service %s", svc.slug)
