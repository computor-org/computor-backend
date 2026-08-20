"""Authenticated client endpoint for creating GitHub issue reports."""

import json
import logging
from json import JSONDecodeError
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.exceptions import BadRequestException, ServiceUnavailableException
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.issue_reports.service import (
    IssueReportNotConfigured,
    IssueReportSubmissionError,
    submit_issue_report,
)
from computor_types.issue_reports import IssueReportCreate, IssueReportCreated

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=IssueReportCreated, status_code=201)
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
        raise ServiceUnavailableException(detail=str(exc)) from exc
    except IssueReportSubmissionError as exc:
        logger.warning("Issue report submission failed: %s", exc)
        raise ServiceUnavailableException(
            detail="The problem report could not be submitted. Please try again later."
        ) from exc
