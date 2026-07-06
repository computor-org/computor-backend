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
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.settings import settings
from computor_types.instance import InstanceInfoGet

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


@instance_router.get("/instance-info", response_model=InstanceInfoGet, tags=["instance"])
async def get_instance_info(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> InstanceInfoGet:
    """Public navigation URLs for this Computor instance."""
    # The web app is served at the root of PUBLIC_DOMAIN; WEB_APP_URL overrides
    # for split/dev deployments where that is not the case.
    web_url = _normalize_url(settings.WEB_APP_URL or settings.PUBLIC_DOMAIN)

    cfg = get_git_server_settings()
    forgejo_url = (
        _normalize_url(cfg.git_server_url)
        if cfg.is_forgejo and cfg.git_server_url
        else None
    )

    return InstanceInfoGet(web_url=web_url, forgejo_url=forgejo_url)
