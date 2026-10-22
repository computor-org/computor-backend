"""Support tickets API (computor-org/issues#520, MVP).

Team queue for ``_support`` / ``_support_agent`` / ``_admin``; see
``support/access.py`` for the rules. Mail is never parsed here: the support
Temporal worker imports it, and replies are handed to that worker, the only
process holding the mailbox credentials.
"""
import logging
from typing import Annotated, List
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.exceptions import ForbiddenException, IssueReportingUnavailableException
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.support import access, reports, service
from computor_backend.support.config import SUPPORT_TASK_QUEUE, get_support_settings
from computor_types.support import (
    SupportAgentRef,
    SupportCapabilities,
    TicketGet,
    TicketList,
    TicketMessageCreate,
    TicketPublishDraft,
    TicketQuery,
    TicketUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _github_publish_available() -> bool:
    from computor_backend.issue_reports.config import get_issue_report_settings
    from computor_backend.issue_reports.health import current_health

    settings = get_issue_report_settings()
    return bool(settings.configured and settings.has_token and current_health().available)


@router.get("/capabilities", response_model=SupportCapabilities)
async def support_capabilities(
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    """What the caller may do in the support queue (UI gating only)."""
    return SupportCapabilities(
        can_publish=access.can_manage(principal) and _github_publish_available(),
        can_view=access.can_view_team_queue(principal),
        can_reply=access.can_manage(principal),
        can_manage=access.can_manage(principal),
        can_write_internal=access.can_write_internal(principal),
        is_admin=bool(principal.is_admin),
        team_addresses=get_support_settings().team_address_list if access.can_manage(principal) else [],
    )


@router.get("/agents", response_model=List[SupportAgentRef])
async def support_agents(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
):
    """Users a ticket can be assigned to (holders of _support or _admin)."""
    return service.list_agents(principal, db)


@router.get("/tickets", response_model=List[TicketList])
async def list_tickets(
    principal: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    params: TicketQuery = Depends(),
    db: Session = Depends(get_db, scope="function"),
):
    items, total = service.list_tickets(params, principal, db)
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get("/tickets/{ticket_id}", response_model=TicketGet)
async def get_ticket(
    ticket_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
):
    return service.get_ticket(ticket_id, principal, db)


@router.post("/tickets/{ticket_id}/claim", response_model=TicketGet)
async def claim_ticket(
    ticket_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
):
    return service.claim_ticket(ticket_id, principal, db)


@router.patch("/tickets/{ticket_id}", response_model=TicketGet)
async def update_ticket(
    ticket_id: str,
    payload: TicketUpdate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
):
    return service.update_ticket(ticket_id, payload, principal, db)


async def _enqueue_delivery(message_id: str, retry: bool = False) -> None:
    import uuid

    from computor_backend.tasks import get_task_executor
    from computor_types.tasks import TaskSubmission

    suffix = f"-retry-{uuid.uuid4().hex[:8]}" if retry else ""
    await get_task_executor().submit_task(TaskSubmission(
        task_name="support_send_reply",
        parameters={"message_id": message_id},
        queue=SUPPORT_TASK_QUEUE,
        workflow_id=f"support-send-{message_id}{suffix}",
    ))


@router.post("/tickets/{ticket_id}/messages", response_model=TicketGet, status_code=201)
async def add_ticket_message(
    ticket_id: str,
    payload: TicketMessageCreate,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
):
    """Internal note (``internal: true``) or mail reply to the reporter."""
    ticket, to_send = service.add_message(ticket_id, payload, principal, db)
    if to_send is None:
        return ticket
    try:
        await _enqueue_delivery(to_send)
    except Exception as exc:  # Temporal unreachable: record, do not lose the text
        logger.exception("support reply %s: could not queue delivery", to_send)
        service.mark_delivery_failed(to_send, f"could not queue delivery: {type(exc).__name__}", db)
        return service.get_ticket(ticket_id, principal, db)
    return ticket


@router.post("/tickets/{ticket_id}/messages/{message_id}/retry", response_model=TicketGet)
async def retry_ticket_message(
    ticket_id: str,
    message_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
):
    """Re-queue a reply whose delivery failed (never one that was sent)."""
    if not access.can_manage(principal):
        raise ForbiddenException(detail="Only support members can send replies")
    ticket = service.get_ticket_or_404(ticket_id, principal, db)
    message_id = service.requeue_failed(ticket, message_id, principal, db)
    try:
        await _enqueue_delivery(message_id, retry=True)
    except Exception as exc:
        service.mark_delivery_failed(message_id, f"could not queue delivery: {type(exc).__name__}", db)
    return service.get_ticket(ticket_id, principal, db)


@router.post("/import", status_code=202)
async def trigger_import(
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    """Run the mail import now (it also runs on a schedule)."""
    if not access.can_manage(principal):
        raise ForbiddenException(detail="Only support members can trigger the mail import")
    import uuid

    from computor_backend.tasks import get_task_executor
    from computor_types.tasks import TaskSubmission
    workflow_id = await get_task_executor().submit_task(TaskSubmission(
        task_name="support_mail_import", parameters={}, queue=SUPPORT_TASK_QUEUE,
        workflow_id=f"support-mail-import-manual-{uuid.uuid4()}",
    ))
    return {"workflow_id": workflow_id}


@router.get("/tickets/{ticket_id}/attachments/{attachment_id}")
async def download_attachment(
    ticket_id: str,
    attachment_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
):
    """Download only: generic type, attachment disposition, no sniffing."""
    att = service.get_attachment(ticket_id, attachment_id, principal, db)
    ascii_name = "".join(c if 32 <= ord(c) < 127 and c not in '"\\;' else "_" for c in att.filename)
    return Response(
        content=bytes(att.data),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": (f'attachment; filename="{ascii_name}"; '
                                    f"filename*=UTF-8''{quote(att.filename)}"),
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/tickets/{ticket_id}/publish-draft", response_model=TicketPublishDraft)
async def get_publish_draft(
    ticket_id: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
):
    """Suggested title/text for publishing; identity-shaped context keys removed.

    The support member must still read and edit it: the reporter's own words
    can name people.
    """
    ticket = service.get_ticket_or_404(ticket_id, principal, db)
    return reports.publish_draft(ticket, principal, db)


@router.post("/tickets/{ticket_id}/publish", response_model=TicketGet)
async def publish_ticket(
    ticket_id: str,
    payload: TicketPublishDraft,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db, scope="function"),
):
    """Publish an anonymised GitHub issue for this ticket (``_support`` only, once).

    Nothing is posted automatically: this is the one deliberate step from a
    ticket to the tracker. The reporter link stays in ``issue_report``.
    """
    from computor_backend.issue_reports.health import ensure_probed
    from computor_backend.issue_reports.service import (
        IssueReportNotConfigured,
        IssueReportSubmissionError,
    )

    if not access.can_manage(principal):
        raise ForbiddenException(detail="Only support members can publish tickets")
    ticket = service.get_ticket_or_404(ticket_id, principal, db)
    health = await ensure_probed()
    if not health.available:
        raise IssueReportingUnavailableException(detail="Publishing to GitHub is not available")
    try:
        await reports.publish_ticket(ticket, payload.title, payload.body, principal, db)
    except (IssueReportNotConfigured, IssueReportSubmissionError) as exc:
        db.rollback()
        logger.warning("publish ticket %s failed: %s", ticket_id, exc)
        raise IssueReportingUnavailableException(
            detail="The ticket could not be published to GitHub."
        ) from exc
    return service.get_ticket(ticket_id, principal, db)
