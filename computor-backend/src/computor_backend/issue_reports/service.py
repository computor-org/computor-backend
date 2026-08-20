"""Submit authenticated Computor reports to the private GitHub issue depot."""

import base64
import json
import logging
import re
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import httpx
from fastapi import UploadFile
from sqlalchemy.orm import Session

from computor_backend.issue_reports.config import IssueReportSettings, get_issue_report_settings
from computor_backend.issue_reports.health import current_health, mark_unhealthy
from computor_backend.model.auth import User
from computor_backend.permissions.principal import Principal
from computor_types.issue_reports import IssueReportCreate, IssueReportCreated

logger = logging.getLogger(__name__)

_SENSITIVE_KEY_RE = re.compile(
    r"(?:token|secret|password|authorization|cookie|credential|private[_-]?key)",
    re.IGNORECASE,
)
_SCREENSHOT_TYPES = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class IssueReportNotConfigured(RuntimeError):
    """Raised when this deployment has not enabled GitHub issue reporting."""


class IssueReportSubmissionError(RuntimeError):
    """Raised when GitHub rejects a report or its attachment."""


def _redact(value: Any, depth: int = 0) -> Any:
    """Redact credential-like context keys and bound diagnostic size."""
    if depth > 5:
        return "[truncated]"
    if isinstance(value, dict):
        return {
            str(key): "[redacted]" if _SENSITIVE_KEY_RE.search(str(key)) else _redact(item, depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item, depth + 1) for item in value[:100]]
    if isinstance(value, str) and len(value) > 4000:
        return f"{value[:4000]}… [truncated]"
    return value


def _require_configuration() -> IssueReportSettings:
    """The configuration a server-side submission needs.

    A token is what makes submitting on the user's behalf possible at all —
    GitHub has no anonymous issue creation — so its absence means this
    deployment does not submit reports, whatever else is set.
    """
    settings = get_issue_report_settings()
    if not settings.configured:
        raise IssueReportNotConfigured("GitHub issue reporting is not configured")
    if not settings.has_token:
        raise IssueReportNotConfigured("GITHUB_ISSUE_REPORT_TOKEN is not set")
    return settings


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "computor-backend-issue-reporter",
    }


def _error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        return str(payload.get("message", response.text))
    except (ValueError, AttributeError):
        return response.text


async def _upload_screenshot(
    client: httpx.AsyncClient,
    settings: IssueReportSettings,
    report_id: str,
    screenshot: UploadFile,
) -> str:
    extension = _SCREENSHOT_TYPES.get((screenshot.content_type or "").lower())
    if extension is None:
        raise IssueReportSubmissionError("Screenshot must be PNG, JPEG, GIF, or WebP")

    contents = await screenshot.read(settings.max_screenshot_bytes + 1)
    if len(contents) > settings.max_screenshot_bytes:
        raise IssueReportSubmissionError("Screenshot is larger than the configured upload limit")

    path = f"issue-reports/{report_id}/screenshot{extension}"
    endpoint = (
        f"{settings.api_base}/repos/{settings.reference.full_name}"
        f"/contents/{quote(path, safe='/')}"
    )
    response = await client.put(
        endpoint,
        headers=_github_headers(settings.token.strip()),
        json={
            "message": f"Add screenshot for user report {report_id}",
            "content": base64.b64encode(contents).decode("ascii"),
            "branch": settings.branch.strip() or "main",
        },
    )
    if response.status_code not in (200, 201):
        raise IssueReportSubmissionError(
            f"GitHub rejected the screenshot ({response.status_code}): {_error_detail(response)}"
        )
    payload = response.json()
    return str(payload.get("content", {}).get("html_url", ""))


def _issue_title(payload: IssueReportCreate) -> str:
    source = (payload.title or payload.description.splitlines()[0]).strip()
    source = " ".join(source.split())
    return f"[User report] {source[:140]}"


def _issue_body(
    payload: IssueReportCreate,
    principal: Principal,
    user: User | None,
    screenshot_url: str | None,
) -> str:
    context = _redact(payload.context)
    context_json = json.dumps(context, indent=2, sort_keys=True, default=str)
    if len(context_json) > 16_000:
        context_json = f"{context_json[:16_000]}\n… [truncated]"

    reporter = f"user_id `{principal.user_id or 'unknown'}`"
    if user and user.email:
        reporter += f" ({user.email})"

    lines = [
        "## Description",
        payload.description,
        "",
        "## Expected behavior",
        payload.expected or "Not provided.",
        "",
        "## Steps to reproduce",
        payload.steps or "Not provided.",
        "",
        "## Client context",
        "```json",
        context_json,
        "```",
        "",
        "## Reporter",
        f"- {reporter}",
    ]
    if screenshot_url:
        lines.extend(["", "## Screenshot", f"[Open screenshot]({screenshot_url})"])
    lines.extend(["", "_Submitted through the Computor issue-reporting endpoint._"])
    return "\n".join(lines)


async def submit_issue_report(
    payload: IssueReportCreate,
    principal: Principal,
    db: Session,
    screenshot: UploadFile | None = None,
) -> IssueReportCreated:
    """Create one GitHub issue and optionally store its screenshot in GitHub."""
    settings = _require_configuration()
    token = settings.token.strip()
    report_id = str(uuid4())
    user = db.get(User, principal.user_id) if principal.user_id else None

    async with httpx.AsyncClient(timeout=30.0) as client:
        screenshot_url = None
        if screenshot is not None:
            screenshot_url = await _upload_screenshot(client, settings, report_id, screenshot)

        response = await client.post(
            f"{settings.api_base}/repos/{settings.reference.full_name}/issues",
            headers=_github_headers(token),
            json={
                "title": _issue_title(payload),
                "body": _issue_body(payload, principal, user, screenshot_url),
                "labels": settings.label_list,
            },
        )
        if response.status_code not in (200, 201):
            logger.warning("GitHub issue creation failed with status %s", response.status_code)
            # A token revoked or a repository moved after startup looks exactly
            # like a broken configuration; stop the feature rather than failing
            # every report individually until the next restart.
            if response.status_code in (401, 403, 404):
                mark_unhealthy(f"GitHub rejected a submission with HTTP {response.status_code}")
            raise IssueReportSubmissionError(
                f"GitHub rejected the issue ({response.status_code}): {_error_detail(response)}"
            )

    issue = response.json()
    # Only a public tracker may be linked back to the reporter; a private one is
    # the maintainer board they are meant not to reach.
    is_public = current_health().is_public
    return IssueReportCreated(
        report_id=report_id,
        issue_number=int(issue["number"]),
        issue_url=issue["html_url"] if is_public else None,
    )
