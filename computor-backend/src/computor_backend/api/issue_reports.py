"""Authenticated client endpoint for creating GitHub issue reports.

The route is always registered so the OpenAPI schema and the generated clients
describe one stable contract — code generation imports this app, so a route that
existed only on configured deployments would make generated output depend on
whoever happened to run ``generate.sh``. Availability is enforced per request
instead:

* not configured for server-side submission -> 404, indistinguishable from an
  endpoint this deployment simply does not have;
* configured but failing its GitHub probe -> 503 (``EXT_007``).

Clients are not expected to discover either by trial: ``GET /instance-info``
reports ``issue_reporting.enabled`` so the entry point is hidden outright.
"""

import json
import logging
from json import JSONDecodeError
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.exceptions import (
    BadRequestException,
    EndpointNotFoundException,
    ForbiddenException,
    IssueReportingUnavailableException,
    NotFoundException,
    RateLimitException,
)
from computor_backend.issue_reports.config import get_issue_report_settings
from computor_backend.issue_reports.health import ensure_probed
from computor_backend.model.issue_report import IssueReport
from computor_backend.issue_reports.service import (
    IssueReportNotConfigured,
    IssueReportSubmissionError,
    submit_issue_report,
)
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.redis_cache import get_redis_client
from computor_types.issue_reports import (
    IssueReportCreate,
    IssueReportCreated,
    IssueReportGet,
)

router = APIRouter()
logger = logging.getLogger(__name__)


async def require_issue_reporting() -> None:
    """Refuse the request unless this deployment can actually submit reports.

    A token is what buys server-side submission — GitHub has no anonymous issue
    creation — so without one there is nothing here to call and the deployment
    says so with a 404 rather than advertising a feature it does not have.
    """
    settings = get_issue_report_settings()
    if not settings.configured or not settings.has_token:
        raise EndpointNotFoundException(
            detail="Issue reporting is not enabled on this deployment"
        )
    health = await ensure_probed()
    if not health.available:
        logger.warning("Rejecting issue report: %s", health.reason)
        raise IssueReportingUnavailableException(
            detail="Problem reporting is temporarily unavailable. Please try again later."
        )


async def _enforce_rate_limit(user_id: str, cache) -> None:
    """Spend one report from this user's budget, or refuse.

    Fixed window per user, Redis-backed so it holds across workers — the same
    shape as the template-download limiter in ``api/courses.py``. Fails open:
    this keeps one frustrated user from filling the maintainers' tracker, it is
    not a security control. ``GITHUB_ISSUE_REPORT_RATE_LIMIT_COUNT=0`` disables it.
    """
    settings = get_issue_report_settings()
    limit = settings.rate_limit_count
    window = settings.rate_limit_seconds
    if limit <= 0 or window <= 0:
        return

    key = f"rate_limit:issue_report:{user_id}"
    try:
        count = await cache.incr(key)
        if count == 1:
            await cache.expire(key, window)
        if count <= limit:
            return
        # Report what is left of the current window, not the whole window, so a
        # client waiting on Retry-After does not wait longer than it must.
        remaining = await cache.ttl(key)
    except Exception as exc:
        logger.error("Issue report rate limit check failed: %s", exc)
        return

    raise RateLimitException(
        detail="You have already sent a problem report. Please wait before sending another.",
        retry_after=remaining if isinstance(remaining, int) and remaining > 0 else window,
        context={"limit": limit, "window_seconds": window},
    )


@router.post(
    "",
    response_model=IssueReportCreated,
    status_code=201,
    dependencies=[Depends(require_issue_reporting)],
)
async def create_issue_report(
    description: Annotated[str, Form()],
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    cache=Depends(get_redis_client),
    title: Annotated[str | None, Form()] = None,
    expected: Annotated[str | None, Form()] = None,
    steps: Annotated[str | None, Form()] = None,
    context: Annotated[str, Form()] = "{}",
    screenshot: Annotated[UploadFile | None, File()] = None,
) -> IssueReportCreated:
    """Create a GitHub issue without exposing GitHub credentials to clients."""
    await _enforce_rate_limit(permissions.get_user_id_or_throw(), cache)

    try:
        parsed_context = json.loads(context)
    except (TypeError, JSONDecodeError) as exc:
        raise BadRequestException(detail="Issue report context must be valid JSON") from exc
    if not isinstance(parsed_context, dict):
        raise BadRequestException(detail="Issue report context must be a JSON object")

    payload = IssueReportCreate(
        title=title,
        description=description,
        expected=expected,
        steps=steps,
        context=parsed_context,
    )
    try:
        return await submit_issue_report(payload, permissions, db, screenshot)
    except IssueReportNotConfigured as exc:
        # Configuration changed between the gate and the submission.
        raise EndpointNotFoundException(detail=str(exc)) from exc
    except IssueReportSubmissionError as exc:
        logger.warning("Issue report submission failed: %s", exc)
        raise IssueReportingUnavailableException(
            detail="The problem report could not be submitted. Please try again later."
        ) from exc


@router.get("/{report_id}", response_model=IssueReportGet)
async def get_issue_report(
    report_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> IssueReportGet:
    """Resolve a report id to the person who filed it.

    The GitHub issue names nobody on purpose, so this is the only way back from
    a report to a reporter — and it is admin-only precisely because that is a
    step someone should have to take deliberately.
    """
    if not permissions.is_admin:
        raise ForbiddenException(detail="Requires _admin role")

    # UUID columns want strings here, not uuid.UUID objects.
    record = db.query(IssueReport).filter(IssueReport.id == str(report_id)).first()
    if record is None:
        raise NotFoundException(detail="Issue report not found")

    user = record.user
    return IssueReportGet(
        id=str(record.id),
        user_id=str(record.user_id) if record.user_id else None,
        user_email=user.email if user else None,
        given_name=user.given_name if user else None,
        family_name=user.family_name if user else None,
        repository=record.repository,
        issue_number=record.issue_number,
        issue_url=record.issue_url,
        submitted_at=record.submitted_at,
    )
