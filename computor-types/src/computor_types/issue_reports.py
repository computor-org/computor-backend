"""DTOs for client-submitted issue reports."""

from datetime import datetime
from typing import Any, Optional

from pydantic import AnyHttpUrl, BaseModel, Field


class IssueReportCreate(BaseModel):
    """Text and client context for a user-submitted issue report."""

    title: Optional[str] = Field(default=None, max_length=160)
    description: str = Field(min_length=1, max_length=12_000)
    expected: Optional[str] = Field(default=None, max_length=12_000)
    steps: Optional[str] = Field(default=None, max_length=12_000)
    context: dict[str, Any] = Field(default_factory=dict)


class IssueReportCreated(BaseModel):
    """Receipt handed back to the reporter after a report is filed.

    ``issue_url`` is populated only when the tracker is a *public* repository.
    A private tracker is a maintainer board users are deliberately kept out of —
    the whole reason the token lives in the backend — so linking a reporter into
    it would undo that. They get an identifier to quote instead. For the same
    reason there is no screenshot URL: an uploaded screenshot is stored inside
    that same private repository.
    """

    report_id: str = Field(
        description="Opaque identifier for this report, safe to show the reporter."
    )
    issue_number: int = Field(description="Issue number in the configured tracker.")
    issue_url: Optional[AnyHttpUrl] = Field(
        default=None,
        description="Link to the created issue; null when the tracker is private.",
    )
    screenshot_attached: bool = Field(
        default=False,
        description="Whether an attached screenshot actually made it into the issue. "
        "False when none was sent, or when storing it failed and the report was "
        "filed without it.",
    )


class IssueReportGet(BaseModel):
    """Who filed a report — the half deliberately absent from the GitHub issue.

    Admin-only. The issue itself names nobody, so this lookup is the only way
    back from a report id to a person, and asking for it is an act a maintainer
    performs knowingly rather than a detail they stumble over in the tracker.
    """

    id: str = Field(description="Report id, as quoted in the issue body.")
    user_id: Optional[str] = Field(
        None,
        description="Reporter; null once the account has been deleted.",
    )
    user_email: Optional[str] = Field(
        None, description="Reporter's email, resolved at read time."
    )
    given_name: Optional[str] = Field(None, description="Reporter's given name.")
    family_name: Optional[str] = Field(None, description="Reporter's family name.")
    repository: str = Field(description="Tracker the report was filed in.")
    issue_number: Optional[int] = Field(
        None, description="Issue number; null if the submission never reached GitHub."
    )
    issue_url: Optional[str] = Field(None, description="Link to the created issue.")
    submitted_at: datetime = Field(description="When the report was submitted.")
