"""Instance info and instance status endpoints.

Exposes the handful of public navigation URLs a client needs (the web app and
the managed Forgejo git server) — nothing internal (no Coder/MinIO/Temporal).

Requires authentication but is WHITELISTED in the consent gate
(middleware/consent.py: EXEMPT_GET_PATHS_EXACT), so a consent-blocked client
(e.g. the VSCode extension, which otherwise only sees an opaque 403) can still
fetch this to learn where to go and accept the current privacy policy.

``GET /instance-status`` sits alongside it and is a different thing: runtime
state of this deployment, admin-only, and NOT consent-exempt. It is kept out of
/instance-info precisely because that one is public to every client (#350).
"""
from typing import Annotated

from fastapi import APIRouter, Depends

from computor_backend.business_logic import build_info
from computor_backend.exceptions import ForbiddenException
from computor_backend.git_server.config import get_git_server_settings
from computor_backend.issue_reports.config import get_issue_report_settings
from computor_backend.issue_reports.health import current_health
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import check_admin
from computor_backend.permissions.principal import Principal
from computor_backend.settings import settings
from computor_types.instance import (
    InstanceInfoGet,
    InstanceStatusGet,
    IssueReportingInfo,
)

instance_router = APIRouter()

# Its own router so it can carry its own OpenAPI tag. The client generator gives
# one class per tag and derives that class's base path from the endpoints in it,
# so /instance-status sharing a tag with /instance-info would collapse both into
# one client that can only reach whichever it saw last.
instance_status_router = APIRouter()


def _normalize_url(value: str | None) -> str | None:
    """Trim trailing slashes and ensure a scheme (default https) so the value is
    a well-formed base URL clients can open directly."""
    url = (value or "").strip().rstrip("/")
    if not url:
        return None
    if "://" not in url:
        url = f"https://{url}"
    return url


def _issue_reporting() -> IssueReportingInfo:
    """Report the deployment's problem-reporting capability.

    This is what lets a client hide its entry point instead of discovering the
    endpoint's 404 or 503 by trial. The repository name is deliberately absent:
    a private board is one users must not be pointed at, so only a *public*
    tracker's URL is ever disclosed.
    """
    health = current_health()
    settings_ = get_issue_report_settings()
    return IssueReportingInfo(
        enabled=health.available,
        visibility=health.visibility,
        issues_url=settings_.issues_url if health.available and health.is_public else None,
    )


@instance_router.get("/instance-info", response_model=InstanceInfoGet, tags=["instance"])
async def get_instance_info(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> InstanceInfoGet:
    """Public navigation URLs for this Computor instance."""
    # The web app is served at the root of PUBLIC_DOMAIN; WEB_APP_URL overrides
    # for split/dev deployments where that is not the case.
    web_url = _normalize_url(settings.WEB_APP_URL or settings.PUBLIC_DOMAIN)

    cfg = get_git_server_settings()
    # Surface the user-reachable URL, never the backend-internal container host.
    forgejo_url = (
        _normalize_url(cfg.public_url)
        if cfg.is_forgejo and cfg.git_server_url
        else None
    )

    return InstanceInfoGet(
        web_url=web_url,
        forgejo_url=forgejo_url,
        issue_reporting=_issue_reporting(),
    )


@instance_status_router.get("/instance-status", response_model=InstanceStatusGet)
async def get_instance_status(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> InstanceStatusGet:
    """When this API last restarted and what it is running (#350).

    Admin-only. Nothing here is a secret in itself — a commit hash and two
    timestamps — but it describes the deployment rather than serving the user,
    and the operator asking for it is the only one it helps.
    """
    if not check_admin(principal):
        raise ForbiddenException(
            detail="Only administrators may read the instance status.",
        )

    commit, branch = build_info.running_version()
    return InstanceStatusGet(
        started_at=build_info.started_at(),
        uptime_seconds=build_info.uptime_seconds(),
        commit=commit,
        branch=branch,
        build_time=build_info.build_time(),
    )
