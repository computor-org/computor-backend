"""Auto-generated client for /sessions endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.sessions import (
    SessionCreate,
    SessionGet,
    SessionList,
    SessionUpdate,
)

from computor_client.base import BaseEndpointClient


class SessionsClient(BaseEndpointClient):
    """Client for /sessions endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/sessions",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_sessions(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_sessions(**params)
        return await self.get_sessions()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_session_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_session_by_id(id)

    async def post_sessions(self, payload: SessionCreate) -> SessionGet:
        """Create Sessions"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return SessionGet.model_validate(data)
        return data

    async def get_sessions(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, user_id: Optional[str] = None, session_id: Optional[str] = None, active_only: Optional[str] = None, ip_address: Optional[str] = None) -> List[SessionList]:
        """List Sessions"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'user_id', 'session_id', 'active_only', 'ip_address'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [SessionList.model_validate(item) for item in data]
        return data

    async def get_session_by_id(self, id: str) -> SessionGet:
        """Get Sessions"""
        data = await self._request("GET", f"/{id}")
        if data:
            return SessionGet.model_validate(data)
        return data

    async def patch_session_by_id(self, id: str, payload: SessionUpdate) -> SessionGet:
        """Update Sessions"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return SessionGet.model_validate(data)
        return data

    async def delete_session_by_id(self, id: str) -> Any:
        """Delete Sessions"""
        data = await self._request("DELETE", f"/{id}")
