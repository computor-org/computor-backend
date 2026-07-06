"""Instance/deployment info exposed to authenticated clients.

Surfaced by ``GET /instance-info`` so clients (notably the VSCode extension)
can deep-link users to the web app and the git server. The endpoint is
whitelisted in the consent gate, so a consent-blocked-but-authenticated client
can still discover where to go to give consent.

Deliberately minimal: only the URLs a client legitimately needs to navigate.
No internal service URLs (Coder, MinIO, Temporal, Keycloak admin, …).
"""
from typing import Optional

from pydantic import BaseModel, Field


class InstanceInfoGet(BaseModel):
    """Public navigation URLs for this Computor instance."""

    web_url: Optional[str] = Field(
        None,
        description="Public base URL of the Computor web app "
        "(e.g. https://computor.example.org); null if not configured.",
    )
    forgejo_url: Optional[str] = Field(
        None,
        description="Public base URL of the managed Forgejo git server; "
        "null if no managed Forgejo is configured.",
    )
