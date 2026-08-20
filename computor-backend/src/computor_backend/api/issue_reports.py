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

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.exceptions import (
    BadRequestException,
    EndpointNotFoundException,
    IssueReportingUnavailableException,
)
from computor_backend.issue_reports.config import get_issue_report_settings
from computor_backend.issue_reports.health import ensure_probed
from computor_backend.issue_reports.service import (
    IssueReportNotConfigured,
    IssueReportSubmissionError,
    submit_issue_report,
)
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_types.issue_reports import IssueReportCreate, IssueReportCreated

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
    title: Annotated[str | None, Form()] = None,
    expected: Annotated[str | None, Form()] = None,
    steps: Annotated[str | None, Form()] = None,
    context: Annotated[str, Form()] = "{}",
    screenshot: Annotated[UploadFile | None, File()] = None,
) -> IssueReportCreated:
    """Create a GitHub issue without exposing GitHub credentials to clients."""
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
