"""DTOs for client-submitted issue reports."""

from typing import Any

from pydantic import AnyHttpUrl, BaseModel, Field


class IssueReportCreate(BaseModel):
    """Text and client context for a user-submitted issue report."""

    title: str | None = Field(default=None, max_length=160)
    description: str = Field(min_length=1, max_length=12_000)
    expected: str | None = Field(default=None, max_length=12_000)
    steps: str | None = Field(default=None, max_length=12_000)
    context: dict[str, Any] = Field(default_factory=dict)


class IssueReportCreated(BaseModel):
    """GitHub issue identity returned to the client after submission."""

    issue_number: int
    issue_url: AnyHttpUrl
    screenshot_url: AnyHttpUrl | None = None
