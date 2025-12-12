"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.messages import (
    MessageCreate,
    MessageGet,
    MessageList,
    MessageUpdate,
)

from computor_client.http import AsyncHTTPClient


class MessagesClient:
    """
    Client for messages endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        data: Union[MessageCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> MessageGet:
        """Create Message"""
        response = await self._http.post(f"/messages", json_data=data, params=kwargs)
        return MessageGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[MessageList]:
        """List Messages"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/messages",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [MessageList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> MessageGet:
        """Get Message"""
        response = await self._http.get(f"/messages/{id}", params=kwargs)
        return MessageGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[MessageUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> MessageGet:
        """Update Message"""
        response = await self._http.patch(f"/messages/{id}", json_data=data, params=kwargs)
        return MessageGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Message"""
        await self._http.delete(f"/messages/{id}", params=kwargs)
        return

    async def reads(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Mark Message Read"""
        response = await self._http.post(f"/messages/{id}/reads", params=kwargs)
        return

    async def delete_reads(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Mark Message Unread"""
        await self._http.delete(f"/messages/{id}/reads", params=kwargs)
        return

    async def audit(
        self,
        id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Message Audit"""
        response = await self._http.get(f"/messages/{id}/audit", params=kwargs)
        return response.json()

