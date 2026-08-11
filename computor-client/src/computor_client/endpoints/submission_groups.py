"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.submission_groups import (
    SubmissionGroupCreate,
    SubmissionGroupGet,
    SubmissionGroupList,
    SubmissionGroupUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class SubmissionGroupsClient:
    """
    Client for submission groups endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[SubmissionGroupList]:
        """List Submission-Groups"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[SubmissionGroupList]:
        """List Submission-Groups (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/submission-groups", params=params)
        return Page.from_response(response, SubmissionGroupList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[SubmissionGroupCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGroupGet:
        """Create Submission-Groups"""
        response = await self._http.post("/submission-groups", json_data=data, params=kwargs)
        return SubmissionGroupGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Submission-Groups"""
        await self._http.delete(f"/submission-groups/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> SubmissionGroupGet:
        """Get Submission-Groups"""
        response = await self._http.get(f"/submission-groups/{quote_path(id)}", params=kwargs)
        return SubmissionGroupGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[SubmissionGroupUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SubmissionGroupGet:
        """Update Submission-Groups"""
        response = await self._http.patch(f"/submission-groups/{quote_path(id)}", json_data=data, params=kwargs)
        return SubmissionGroupGet.model_validate(response.json())

