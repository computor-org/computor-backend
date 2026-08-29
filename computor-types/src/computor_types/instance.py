"""Instance/deployment info exposed to authenticated clients.

Two endpoints, deliberately apart. ``GET /instance-info`` is discovery: the URLs
any client needs, consent-exempt and safe for everyone. ``GET /instance-status``
is runtime state about the deployment itself, and is admin-only.

Surfaced by ``GET /instance-info`` so clients (notably the VSCode extension)
can deep-link users to the web app and the git server. The endpoint is
whitelisted in the consent gate, so a consent-blocked-but-authenticated client
can still discover where to go to give consent.

Deliberately minimal: only the URLs a client legitimately needs to navigate.
No internal service URLs (Coder, MinIO, Temporal, Keycloak admin, …).
"""
from datetime import datetime
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


class InstanceStatusGet(BaseModel):
    """Runtime state of the running API (#350).

    Answers "when did this last restart, and what is it running", which nothing
    in the UI could say before.

    Readable by any authenticated user, with one field redacted rather than a
    second response shape: ``commit`` is admin-only. A restart time, an uptime
    and a branch name are a version label — the sidebar already shows the web
    image's own commit to everyone — but the full SHA pins the exact source of a
    public repository, which is the operator's business and nobody else's.

    The issue also asks for system and workspace memory. That is deliberately
    absent rather than null: the API holds no docker socket and there is no
    metrics collector, so the only workspace memory figure available is the
    per-template *cap* pushed at template-push time. Reporting a reservation
    under the label "usage" would be worse than reporting nothing, so the
    memory half stays open until there is something real to measure.
    """

    started_at: datetime = Field(
        description="When this API process came up (UTC). The last server restart.",
    )
    uptime_seconds: int = Field(
        description="Seconds since started_at, so a client need not trust its own clock.",
    )
    commit: Optional[str] = Field(
        None,
        description="Commit hash of the running code; 'unknown' if it cannot be "
        "determined, and null for a non-admin reader, who is not shown it.",
    )
    branch: str = Field(
        description="Branch the running code was built from; 'unknown' if undeterminable.",
    )
    build_time: Optional[datetime] = Field(
        None,
        description="When the running image was built (UTC). Null in development, "
        "where the API runs from a working tree and there is no build.",
    )
