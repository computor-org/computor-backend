"""Instance/deployment info exposed to authenticated clients.

Surfaced by ``GET /instance-info`` so clients (notably the VSCode extension)
can deep-link users to the web app and the git server. The endpoint is
whitelisted in the consent gate, so a consent-blocked-but-authenticated client
can still discover where to go to give consent.

Deliberately minimal: only the URLs a client legitimately needs to navigate.
No internal service URLs (Coder, MinIO, Temporal, Keycloak admin, …).
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class IssueReportingInfo(BaseModel):
    """Whether this deployment accepts user problem reports, and how.

    There are only two kinds of issue tracker. A **public** repository needs no
    token — GitHub forbids anonymous issue creation, so the backend cannot file
    on the user's behalf and the client opens ``issues_url`` instead, where the
    user files it with their own GitHub account. A **private** repository is a
    maintainer board users must not reach; the backend holds a token and files
    for them, and no link is ever handed back.

    ``visibility`` is read from GitHub by the startup probe, never guessed from
    configuration.
    """

    enabled: bool = Field(
        description="Whether to offer a reporting entry point at all. False when "
        "the deployment has no tracker configured or its probe is failing.",
    )
    visibility: Optional[Literal["public", "private"]] = Field(
        None,
        description="Visibility of the configured repository; null while unknown.",
    )
    issues_url: Optional[str] = Field(
        None,
        description="GitHub issues page to open directly. Set only for a public "
        "repository — a private board is never linked to a reporter.",
    )


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
    issue_reporting: Optional[IssueReportingInfo] = Field(
        None,
        description="Problem-reporting capability of this deployment.",
    )
