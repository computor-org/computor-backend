"""Startup connectivity probe for GitHub issue reporting.

Configuration says *whether* a deployment declares an issue tracker; this module
says whether that tracker actually works, and whether it is public or private —
read from GitHub rather than guessed.

The result gates the feature at runtime: an unhealthy probe makes
``POST /issue-reports`` answer 503 and makes ``GET /instance-info`` report the
feature as disabled, which is what hides the entry point in clients. It cannot
un-register the route — FastAPI builds the app before the lifespan runs — so
publication stays a pure configuration decision (see ``api/issue_reports.py``).

Re-probes lazily on a TTL while unhealthy, so a rotated token or a transient
GitHub outage recovers without a backend restart.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, replace
from typing import Optional

import httpx

from computor_backend.issue_reports.config import IssueReportSettings, get_issue_report_settings

logger = logging.getLogger(__name__)

# How long an unhealthy verdict is trusted before the next request re-probes.
REPROBE_TTL_SECONDS = 300.0
PROBE_TIMEOUT_SECONDS = 10.0

PUBLIC = "public"
PRIVATE = "private"


@dataclass(frozen=True)
class IssueReportingHealth:
    """Last known state of the configured issue tracker."""

    available: bool = False
    reason: str = "not configured"
    visibility: Optional[str] = None
    checked_at: Optional[float] = None

    @property
    def is_public(self) -> bool:
        return self.visibility == PUBLIC


_state = IssueReportingHealth()
_lock = asyncio.Lock()


def current_health() -> IssueReportingHealth:
    """The cached verdict, without touching the network."""
    return _state


def reset_health() -> None:
    """Drop the cached verdict (tests, and after an env change)."""
    global _state
    _state = IssueReportingHealth()


def mark_unhealthy(reason: str) -> None:
    """Record that a live GitHub call failed the way a broken configuration would.

    Called when a real submission is rejected with an auth/not-found status, so
    a token revoked after startup stops the feature instead of failing every
    report one by one.
    """
    global _state
    _state = replace(_state, available=False, reason=reason, checked_at=time.monotonic())
    logger.warning("Issue reporting marked unavailable: %s", reason)


def _record(available: bool, reason: str, visibility: Optional[str]) -> IssueReportingHealth:
    global _state
    _state = IssueReportingHealth(
        available=available,
        reason=reason,
        visibility=visibility,
        checked_at=time.monotonic(),
    )
    return _state


def _headers(settings: IssueReportSettings) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "computor-backend-issue-reporter",
    }
    if settings.has_token:
        headers["Authorization"] = f"Bearer {settings.token.strip()}"
    return headers


async def probe_issue_reporting() -> IssueReportingHealth:
    """Ask GitHub whether the configured repository can receive reports.

    Never raises and never logs the token. Write permission cannot be verified
    without creating an issue, so it is only ever proven by the first real
    submission.
    """
    settings = get_issue_report_settings()
    reference = settings.reference
    if reference is None:
        if settings.repository.strip():
            return _record(
                False,
                "GITHUB_ISSUE_REPORT_REPOSITORY is not a GitHub repository "
                "(expected owner/name or a github.com URL)",
                None,
            )
        return _record(False, "not configured", None)

    url = f"{settings.api_base}/repos/{reference.owner}/{reference.name}"
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=_headers(settings))
    except httpx.HTTPError as exc:
        return _record(False, f"GitHub is unreachable ({type(exc).__name__})", None)

    if response.status_code in (401, 403):
        return _record(False, "GitHub rejected GITHUB_ISSUE_REPORT_TOKEN", None)
    if response.status_code == 404:
        # A private repository is invisible to an unauthenticated caller, so an
        # anonymous 404 is far more often a missing token than a typo.
        reason = (
            f"{reference.full_name} not found — the token has no access to it"
            if settings.has_token
            else f"{reference.full_name} is private or does not exist — "
            "set GITHUB_ISSUE_REPORT_TOKEN to report into a private repository"
        )
        return _record(False, reason, None)
    if response.status_code != 200:
        return _record(False, f"GitHub returned HTTP {response.status_code}", None)

    try:
        payload = response.json()
    except ValueError:
        return _record(False, "GitHub returned an unreadable repository payload", None)

    visibility = PRIVATE if payload.get("private") else PUBLIC
    if not payload.get("has_issues", False):
        return _record(
            False, f"{reference.full_name} has its issue tracker disabled", visibility
        )
    if visibility == PRIVATE and not settings.has_token:
        return _record(
            False,
            f"{reference.full_name} is private — set GITHUB_ISSUE_REPORT_TOKEN",
            visibility,
        )
    return _record(True, "", visibility)


async def ensure_probed() -> IssueReportingHealth:
    """Health for a request, re-probing an unhealthy verdict once per TTL."""
    state = _state
    if state.available:
        return state
    if state.checked_at is not None and time.monotonic() - state.checked_at < REPROBE_TTL_SECONDS:
        return state
    async with _lock:
        # Another request may have re-probed while we waited for the lock.
        if _state.available or (
            _state.checked_at is not None
            and _state.checked_at != state.checked_at
            and time.monotonic() - _state.checked_at < REPROBE_TTL_SECONDS
        ):
            return _state
        return await probe_issue_reporting()


def describe(health: IssueReportingHealth) -> str:
    """One-line startup summary."""
    settings = get_issue_report_settings()
    reference = settings.reference
    target = reference.full_name if reference else "(unconfigured)"
    if health.available:
        summary = f"issue reporting enabled for {target} ({health.visibility})"
        if health.is_public and settings.has_token:
            summary += " — the repository is public, so the token is unused and clients link to it directly"
        return summary
    return f"issue reporting disabled for {target}: {health.reason}"
