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
Only the ``services:`` and ``example_repositories:`` sections are applied here —
organizations/users/contents are out of scope for boot seeding.

The ``example_repositories:`` section seeds a default Example Repository so a
fresh install has somewhere to upload examples into (MinIO-backed by default);
it is idempotent on ``source_url`` (the model's unique key).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from computor_types.api_tokens import ApiTokenAdminCreate
from computor_types.deployments_refactored import (
    ComputorDeploymentConfig,
    ExampleRepositoryConfig,
    ServiceConfig,
)
from computor_types.services import ServiceCreate

from computor_backend.business_logic.api_tokens import create_api_token_admin
from computor_backend.business_logic.service_accounts import create_service_account
from computor_backend.database import get_db_session
from computor_backend.model.example import ExampleRepository
from computor_backend.model.service import ApiToken, Service
from computor_backend.permissions.principal import Principal

logger = logging.getLogger(__name__)


def _deployments_dir() -> str:
    """Directory of bootstrap deployment YAMLs.

    Prod sets ``DEPLOYMENTS_DIR`` (the container mounts the staged dir there). In
    dev the API runs from ``computor-backend/src`` (api.sh), NOT the repo root, so
    a cwd-relative path won't find ``data/deployments`` — resolve it relative to
    the repo root instead (this file is at
    ``<repo>/computor-backend/src/computor_backend/business_logic/bootstrap.py``).
    """
    env = os.environ.get("DEPLOYMENTS_DIR")
    if env:
        return env
    repo_root = Path(__file__).resolve().parents[4]
    return str(repo_root / "data" / "deployments")


def ensure_bootstrap_services() -> None:
    """Apply the ``services:`` of every ``data/deployments/*.yaml`` idempotently.

    Prints ``[STARTUP] Bootstrap services: ...`` lines (visible in the API log,
    like the other startup steps) so an empty/missing dir or a per-service result
    is observable.
    """
    deployments_dir = _deployments_dir()
    if not os.path.isdir(deployments_dir):
        print(f"[STARTUP] Bootstrap services: no deployments dir at {deployments_dir} — skipping")
        return

    files = sorted(
        f
        for f in os.listdir(deployments_dir)
        if f.endswith((".yaml", ".yml")) and not f.endswith((".example.yaml", ".example.yml"))
    )
    if not files:
        print(f"[STARTUP] Bootstrap services: no deployment files in {deployments_dir} (only examples?)")
        return

    print(f"[STARTUP] Bootstrap services: applying {len(files)} file(s) from {deployments_dir}")
    system = Principal(is_admin=True)  # trusted boot context; created_by stays NULL
    with get_db_session() as db:
        for fname in files:
            path = os.path.join(deployments_dir, fname)
            try:
                with open(path, "r") as fh:
                    data = yaml.safe_load(fh) or {}
                config = ComputorDeploymentConfig(**data)
            except Exception as exc:  # noqa: BLE001 - one bad file shouldn't block the rest
                print(f"[STARTUP] Bootstrap services: {fname} is invalid, skipping: {exc}")
                continue

            for svc in (config.services or []):
                try:
                    status = _ensure_service(svc, system, db)
                    print(f"[STARTUP] Bootstrap service '{svc.slug}': {status}")
                except Exception as exc:  # noqa: BLE001 - best-effort per service
                    print(f"[STARTUP] Bootstrap service '{getattr(svc, 'slug', '?')}' failed: {exc}")

            for repo in (config.example_repositories or []):
                try:
                    status = _ensure_example_repository(repo, system, db)
                    print(f"[STARTUP] Bootstrap example repository '{repo.name}': {status}")
                except Exception as exc:  # noqa: BLE001 - best-effort per repository
                    print(
                        f"[STARTUP] Bootstrap example repository "
                        f"'{getattr(repo, 'name', '?')}' failed: {exc}"
                    )


def _ensure_service(svc: ServiceConfig, system: Principal, db) -> str:
    """Ensure one service + its token exist. Returns a short human status."""
    existing = db.query(Service).filter(Service.slug == svc.slug).first()
    if existing is None:
        created = create_service_account(
            ServiceCreate(
                slug=svc.slug,
                name=(svc.user.given_name or svc.slug.replace("-", " ").replace(".", " ").title()),
                description=svc.description or f"Service for {svc.slug}",
                service_type=svc.service_type_path,
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
        created_now = True
    else:
        user_id = str(existing.user_id)
        created_now = False

    # Token is idempotent: leave any existing active token untouched (a changed
    # ${TESTING_WORKER_TOKEN} is intentionally NOT auto-rotated here — that would
    # silently break a running worker; rotate it deliberately instead).
    has_token = (
        db.query(ApiToken)
        .filter(ApiToken.user_id == user_id, ApiToken.revoked_at.is_(None))
        .first()
    )
    if has_token is not None:
        return "created (token already present)" if created_now else "already present"

    raw = svc.api_token.token if svc.api_token else None
    if not raw:
        return f"{'created' if created_now else 'present'} WITHOUT a token (no api_token.token in YAML)"

    token = os.path.expandvars(raw)
    if not token or token.startswith("${") or not token.startswith("ctp_") or len(token) < 32:
        return (
            f"{'created' if created_now else 'present'} WITHOUT a token — api_token did not resolve "
            f"to a valid 'ctp_' token (is TESTING_WORKER_TOKEN set & exported in the API's env?)"
        )

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
    return f"{'created' if created_now else 'present'} + token set"


def _ensure_example_repository(cfg: ExampleRepositoryConfig, system: Principal, db) -> str:
    """Ensure one Example Repository exists. Returns a short human status.

    Idempotent on ``source_url`` (the model's unique key). ``created_by`` stays
    NULL — this is the trusted boot context, mirroring ``_ensure_service``. For
    object-store repos (minio/s3) the target bucket is ensured best-effort so
    uploads work out of the box without blocking startup on MinIO availability.
    """
    existing = (
        db.query(ExampleRepository)
        .filter(ExampleRepository.source_url == cfg.source_url)
        .first()
    )
    if existing is not None:
        return "already present"

    repo = ExampleRepository(
        name=cfg.name,
        description=cfg.description,
        source_type=cfg.source_type,
        source_url=cfg.source_url,
        organization_id=cfg.organization_id,
    )
    db.add(repo)
    db.flush()

    if cfg.source_type in ("minio", "s3"):
        bucket = cfg.source_url.split("/")[0]
        try:
            from computor_backend.minio_client import get_minio_client

            client = get_minio_client()
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                return f"created + bucket '{bucket}' created"
            return f"created (bucket '{bucket}' present)"
        except Exception as exc:  # noqa: BLE001 - MinIO may be down; repo row still stands
            return f"created WITHOUT ensuring bucket '{bucket}' (MinIO unavailable: {exc})"

    return "created"
