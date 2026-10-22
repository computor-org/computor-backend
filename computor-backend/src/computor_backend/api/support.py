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
from computor_backend.exceptions import ForbiddenException
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.support import access, service
from computor_backend.support.config import SUPPORT_TASK_QUEUE, get_support_settings
from computor_types.support import (
    SupportAgentRef,
    SupportCapabilities,
    TicketGet,
    TicketList,
    TicketMessageCreate,
    TicketQuery,
    TicketUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/capabilities", response_model=SupportCapabilities)
async def support_capabilities(
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    """What the caller may do in the support queue (UI gating only)."""
    return SupportCapabilities(
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
