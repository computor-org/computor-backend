"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.messages import (
    MessageCreate,
    MessageGet,
    MessageList,
    MessageMentionRef,
    MessageReadBulk,
    MessageReadBulkResult,
    MessageThread,
    MessageUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class MessagesClient:
    """
    Client for messages endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[MessageList]:
        """List Messages"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[MessageList]:
        """List Messages (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/messages", params=params)
        return Page.from_response(response, MessageList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[MessageCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> MessageGet:
        """Create Message"""
        response = await self._http.post("/messages", json_data=data, params=kwargs)
        return MessageGet.model_validate(response.json())

    async def list_mentionable_users(
        self,
        **kwargs: Any,
    ) -> List[MessageMentionRef]:
        """List Mentionable Users Endpoint"""
        response = await self._http.get("/messages/mentionable-users", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [MessageMentionRef.model_validate(item) for item in data]
        return []

    async def reads_bulk(
        self,
        data: Union[MessageReadBulk, Dict[str, Any]],
        **kwargs: Any,
    ) -> MessageReadBulkResult:
        """Mark Messages Read Bulk"""
        response = await self._http.post("/messages/reads/bulk", json_data=data, params=kwargs)
        return MessageReadBulkResult.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Message"""
        await self._http.delete(f"/messages/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> MessageGet:
        """Get Message"""
        response = await self._http.get(f"/messages/{quote_path(id)}", params=kwargs)
        return MessageGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[MessageUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> MessageGet:
        """Update Message"""
        response = await self._http.patch(f"/messages/{quote_path(id)}", json_data=data, params=kwargs)
        return MessageGet.model_validate(response.json())

    async def get_audit(
        self,
        id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Message Audit"""
        response = await self._http.get(f"/messages/{quote_path(id)}/audit", params=kwargs)
        return response.json()

    async def delete_reads(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Mark Message Unread"""
        await self._http.delete(f"/messages/{quote_path(id)}/reads", params=kwargs)
        return

    async def reads(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Mark Message Read"""
        await self._http.post(f"/messages/{quote_path(id)}/reads", params=kwargs)
        return

    async def get_thread(
        self,
        id: str,
        **kwargs: Any,
    ) -> MessageThread:
        """Get Message Thread Endpoint"""
        response = await self._http.get(f"/messages/{quote_path(id)}/thread", params=kwargs)
        return MessageThread.model_validate(response.json())

