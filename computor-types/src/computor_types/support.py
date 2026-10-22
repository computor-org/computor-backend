"""DTOs for support tickets (team mail and problem reports, issues#520).

A ticket's conversation is a list of messages. Messages with
``visibility == "internal"`` are team notes; they are only ever returned to
holders of ``_support``, ``_support_agent`` or ``_admin``.

Mail bodies are parsed in the backend only. ``text`` is plain text; ``html``,
when present, has been sanitised server-side (allowlist, no remote content,
no scripts, no styles that load anything) and is meant for a sandboxed
iframe, never for direct insertion into the page.
"""

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    DONE = "done"


class TicketChannel(str, Enum):
    MAIL = "mail"
    WEB = "web"
    VSCODE = "vscode"


class TicketPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


TicketScope = Literal["unassigned", "mine", "all", "reported"]
MessageVisibility = Literal["public", "internal"]


class TicketUserRef(BaseModel):
    id: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    email: Optional[str] = None


class TicketList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    number: int
    subject: str
    channel: TicketChannel
    status: TicketStatus
    priority: TicketPriority
    restricted: bool
    mailbox_address: Optional[str] = Field(
        None, description="Team address the ticket was sent to (e.g. contact@computor.at)."
    )
    reporter_email: Optional[str] = None
    reporter_name: Optional[str] = None
    reporter_user_id: Optional[str] = None
    assignee: Optional[TicketUserRef] = None
    message_count: int = 0
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class TicketAttachmentGet(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int
    stored: bool = Field(
        description="False when the attachment exceeded the size cap and is only in the mail archive."
    )


class TicketMessageGet(BaseModel):
    id: str
    visibility: MessageVisibility
    direction: Literal["in", "out", "note"]
    author: Optional[TicketUserRef] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    to: List[str] = Field(default_factory=list)
    cc: List[str] = Field(default_factory=list)
    subject: Optional[str] = None
    text: str
    html: Optional[str] = None
    attachments: List[TicketAttachmentGet] = Field(default_factory=list)
    delivery_state: Optional[str] = Field(
        None, description="Outgoing mail only: queued, sent or failed."
    )
    delivery_error: Optional[str] = None
    created_at: datetime


class TicketEventGet(BaseModel):
    id: str
    kind: str
    actor: Optional[TicketUserRef] = None
    data: dict = Field(default_factory=dict)
    created_at: datetime


class TicketReportInfo(BaseModel):
    """Client context of a problem report (channel ``web`` / ``vscode``)."""

    app: Optional[str] = Field(None, description="Client that filed it, e.g. computor-vscode.")
    version: Optional[str] = Field(None, description="Client version.")
    page: Optional[str] = Field(None, description="Web page the report was filed from.")
    command: Optional[str] = Field(None, description="Editor command or view, if any.")
    context: dict = Field(default_factory=dict, description="Diagnostic context (credentials removed).")


class TicketPublication(BaseModel):
    """The anonymised GitHub issue a support member published (team only)."""

    issue_number: Optional[int] = None
    issue_url: Optional[str] = None
    report_id: str
    published_at: Optional[datetime] = None


class TicketGet(TicketList):
    messages: List[TicketMessageGet] = Field(default_factory=list)
    events: List[TicketEventGet] = Field(default_factory=list)
    report: Optional[TicketReportInfo] = Field(
        None, description="Problem-report context; null for mail tickets."
    )
    publication: Optional[TicketPublication] = Field(
        None, description="Published GitHub issue; only ever returned to the support team."
    )


class TicketPublishDraft(BaseModel):
    """Title and text of the issue to publish. Must not identify the reporter."""

    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=20_000)


class TicketQuery(BaseModel):
    """``scope``: ``reported`` lists the caller's own problem reports."""

    scope: TicketScope = "all"
    status: Optional[TicketStatus] = None
    search: Optional[str] = Field(None, max_length=200)
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=200)


class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assignee_id: Optional[str] = Field(
        None, description="User to assign; must hold _support or _admin."
    )
    unassign: bool = Field(False, description="Clear the assignee.")


class TicketMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    internal: bool = Field(
        False, description="True: internal team note, never sent or shown to the reporter."
    )
    from_address: Optional[str] = Field(
        None,
        description="Team address to reply from; defaults to the address the ticket was sent to.",
    )


class SupportCapabilities(BaseModel):
    can_view: bool
    can_reply: bool
    can_manage: bool
    can_write_internal: bool
    is_admin: bool
    team_addresses: List[str] = Field(default_factory=list)
    can_publish: bool = Field(
        False, description="May publish a ticket as an anonymised GitHub issue "
        "(support member, and the deployment has a working GitHub token)."
    )


class SupportAgentRef(TicketUserRef):
    roles: List[str] = Field(default_factory=list)
