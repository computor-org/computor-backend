"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.submission_group_members import (
    SubmissionGroupMemberCreate,
    SubmissionGroupMemberGet,
    SubmissionGroupMemberList,
    SubmissionGroupMemberUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class SubmissionGroupMembersClient:
    """
    Client for submission group members endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[SubmissionGroupMemberList]:
        """List Submission-Group-Members"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[SubmissionGroupMemberList]:
        """List Submission-Group-Members (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/submission-group-members", params=params)
        return Page.from_response(response, SubmissionGroupMemberList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[SubmissionGroupMemberCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGroupMemberGet:
        """Create Submission-Group-Members"""
        response = await self._http.post("/submission-group-members", json_data=data, params=kwargs)
        return SubmissionGroupMemberGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Submission-Group-Members"""
        await self._http.delete(f"/submission-group-members/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> SubmissionGroupMemberGet:
        """Get Submission-Group-Members"""
        response = await self._http.get(f"/submission-group-members/{quote_path(id)}", params=kwargs)
        return SubmissionGroupMemberGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[SubmissionGroupMemberUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGroupMemberGet:
        """Update Submission-Group-Members"""
        response = await self._http.patch(f"/submission-group-members/{quote_path(id)}", json_data=data, params=kwargs)
        return SubmissionGroupMemberGet.model_validate(response.json())

