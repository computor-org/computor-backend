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

from computor_backend.model.auth import User
from computor_backend.permissions.principal import Principal
from computor_backend.settings import settings
from computor_types.issue_reports import IssueReportCreate, IssueReportCreated

logger = logging.getLogger(__name__)

_REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
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


def _require_configuration() -> tuple[str, str, str, str, list[str]]:
    if not settings.GITHUB_ISSUE_REPORT_ENABLED or not settings.GITHUB_ISSUE_REPORT_TOKEN:
        raise IssueReportNotConfigured("GitHub issue reporting is not enabled")
    repository = settings.GITHUB_ISSUE_REPORT_REPOSITORY.strip()
    if not _REPOSITORY_RE.fullmatch(repository):
        raise IssueReportNotConfigured("GITHUB_ISSUE_REPORT_REPOSITORY must be owner/name")
    labels = [label.strip() for label in settings.GITHUB_ISSUE_REPORT_LABELS.split(",") if label.strip()]
    return (
        settings.GITHUB_ISSUE_REPORT_API_URL,
        repository,
        settings.GITHUB_ISSUE_REPORT_BRANCH.strip() or "main",
        settings.GITHUB_ISSUE_REPORT_TOKEN,
        labels,
    )


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
    api_url: str,
    repository: str,
    branch: str,
    token: str,
    report_id: str,
    screenshot: UploadFile,
) -> str:
    extension = _SCREENSHOT_TYPES.get((screenshot.content_type or "").lower())
    if extension is None:
        raise IssueReportSubmissionError("Screenshot must be PNG, JPEG, GIF, or WebP")

    contents = await screenshot.read(settings.GITHUB_ISSUE_REPORT_MAX_SCREENSHOT_BYTES + 1)
    if len(contents) > settings.GITHUB_ISSUE_REPORT_MAX_SCREENSHOT_BYTES:
        raise IssueReportSubmissionError("Screenshot is larger than the configured upload limit")

    path = f"issue-reports/{report_id}/screenshot{extension}"
    endpoint = f"{api_url}/repos/{repository}/contents/{quote(path, safe='/')}"
    response = await client.put(
        endpoint,
        headers=_github_headers(token),
        json={
            "message": f"Add screenshot for user report {report_id}",
            "content": base64.b64encode(contents).decode("ascii"),
            "branch": branch,
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
    api_url, repository, branch, token, labels = _require_configuration()
    report_id = str(uuid4())
    user = db.get(User, principal.user_id) if principal.user_id else None

    async with httpx.AsyncClient(timeout=30.0) as client:
        screenshot_url = None
        if screenshot is not None:
            screenshot_url = await _upload_screenshot(
                client, api_url, repository, branch, token, report_id, screenshot
            )

        response = await client.post(
            f"{api_url}/repos/{repository}/issues",
            headers=_github_headers(token),
            json={
                "title": _issue_title(payload),
                "body": _issue_body(payload, principal, user, screenshot_url),
                "labels": labels,
            },
        )
        if response.status_code not in (200, 201):
            logger.warning("GitHub issue creation failed with status %s", response.status_code)
            raise IssueReportSubmissionError(
                f"GitHub rejected the issue ({response.status_code}): {_error_detail(response)}"
            )

    issue = response.json()
    return IssueReportCreated(
        issue_number=int(issue["number"]),
        issue_url=issue["html_url"],
        screenshot_url=screenshot_url or None,
    )
