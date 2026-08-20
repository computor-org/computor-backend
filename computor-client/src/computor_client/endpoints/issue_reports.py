"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Optional

from computor_types.issue_reports import (
    IssueReportCreated,
    IssueReportGet,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class IssueReportsClient:
    """
    Client for issue reports endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        description: str,
        screenshot: Optional[bytes] = None,
        title: Optional[str] = None,
        expected: Optional[str] = None,
        steps: Optional[str] = None,
        context: Optional[str] = None,
        **kwargs: Any,
    ) -> IssueReportCreated:
        """Create Issue Report"""
        files = {k: v for k, v in {"screenshot": screenshot}.items() if v is not None}
        form_fields = {k: v for k, v in {"description": description, "title": title, "expected": expected, "steps": steps, "context": context}.items() if v is not None}
        response = await self._http.post("/issue-reports", files=files, data=form_fields, params=kwargs)
        return IssueReportCreated.model_validate(response.json())

    async def get(
        self,
        report_id: str,
        **kwargs: Any,
    ) -> IssueReportGet:
        """Get Issue Report"""
        response = await self._http.get(f"/issue-reports/{quote_path(report_id)}", params=kwargs)
        return IssueReportGet.model_validate(response.json())

