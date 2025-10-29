"""Auto-generated client for /messages endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.messages import (
    MessageCreate,
    MessageGet,
    MessageList,
    MessageUpdate,
)

from computor_client.base import BaseEndpointClient


class MessagesClient(BaseEndpointClient):
    """Client for /messages endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/messages",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_messages(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_messages(**params)
        return await self.get_messages()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_message_by_id(id)

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_message_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_message_by_id(id)

    async def post_messages(self, payload: MessageCreate, user_id: Optional[str] = None) -> MessageGet:
        """Create Message"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return MessageGet.model_validate(data)
        return data

    async def get_messages(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, parent_id: Optional[str] = None, author_id: Optional[str] = None, user_id: Optional[str] = None, course_member_id: Optional[str] = None, submission_group_id: Optional[str] = None, course_group_id: Optional[str] = None, course_content_id: Optional[str] = None, course_id: Optional[str] = None, course_id_all_messages: Optional[str] = None, scope: Optional[str] = None) -> List[MessageList]:
        """List Messages"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'parent_id', 'author_id', 'user_id', 'course_member_id', 'submission_group_id', 'course_group_id', 'course_content_id', 'course_id', 'course_id_all_messages', 'scope'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [MessageList.model_validate(item) for item in data]
        return data

    async def get_message_by_id(self, id: str, user_id: Optional[str] = None) -> MessageGet:
        """Get Message"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}", params=params)
        if data:
            return MessageGet.model_validate(data)
        return data

    async def patch_message_by_id(self, id: str, payload: MessageUpdate, user_id: Optional[str] = None) -> MessageGet:
        """Update Message"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return MessageGet.model_validate(data)
        return data

    async def delete_message_by_id(self, id: str, user_id: Optional[str] = None) -> Any:
        """Delete Message"""
        data = await self._request("DELETE", f"/{id}")

    async def post_message_by_id_read(self, id: str, user_id: Optional[str] = None) -> Any:
        """Mark Message Read"""
        data = await self._request("POST", f"/{id}/reads")

    async def delete_message_by_id_read(self, id: str, user_id: Optional[str] = None) -> Any:
        """Mark Message Unread"""
        data = await self._request("DELETE", f"/{id}/reads")

    async def get_message_by_id_audit(self, id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get Message Audit"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}/audit", params=params)
        if data:
            return Dict[str, Any].model_validate(data)
        return data
