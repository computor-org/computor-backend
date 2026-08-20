"""DTOs for client-submitted issue reports."""

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
