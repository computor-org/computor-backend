"""Instance info endpoint.

Exposes the handful of public navigation URLs a client needs (the web app and
the managed Forgejo git server) — nothing internal (no Coder/MinIO/Temporal).

Requires authentication but is WHITELISTED in the consent gate
(middleware/consent.py: EXEMPT_GET_PATHS_EXACT), so a consent-blocked client
(e.g. the VSCode extension, which otherwise only sees an opaque 403) can still
fetch this to learn where to go and accept the current privacy policy.
"""
from typing import Annotated

from fastapi import APIRouter, Depends

from computor_backend.git_server.config import get_git_server_settings
from computor_backend.issue_reports.config import get_issue_report_settings
from computor_backend.issue_reports.health import current_health
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.settings import settings
from computor_types.instance import InstanceInfoGet, IssueReportingInfo

instance_router = APIRouter()


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
