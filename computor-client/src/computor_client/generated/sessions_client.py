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

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_session_by_id(id)

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_session_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_session_by_id(id)

    async def post_sessions(self, payload: SessionCreate, user_id: Optional[str] = None) -> SessionGet:
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

    async def get_session_by_id(self, id: str, user_id: Optional[str] = None) -> SessionGet:
        """Get Sessions"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}", params=params)
        if data:
            return SessionGet.model_validate(data)
        return data

    async def patch_session_by_id(self, id: str, payload: SessionUpdate, user_id: Optional[str] = None) -> SessionGet:
        """Update Sessions"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return SessionGet.model_validate(data)
        return data

    async def delete_session_by_id(self, id: str, user_id: Optional[str] = None) -> Any:
        """Delete Sessions"""
        data = await self._request("DELETE", f"/{id}")

    async def get_sessions_me(self, user_id: Optional[str] = None) -> List[SessionList]:
        """List My Sessions"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", "/me", params=params)
        if isinstance(data, list):
            return [SessionList.model_validate(item) for item in data]
        return data

    async def get_sessions_me_current(self, user_id: Optional[str] = None) -> SessionGet:
        """Get Current Session"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", "/me/current", params=params)
        if data:
            return SessionGet.model_validate(data)
        return data

    async def delete_session_me_by_session_id(self, session_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Revoke My Session"""
        data = await self._request("DELETE", f"/me/{session_id}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def delete_session_me_all(self, include_current: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Revoke All My Sessions"""
        data = await self._request("DELETE", "/me/all")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_session_admin_user_by_user_id(self, user_id: str, active_only: Optional[str] = None) -> List[SessionGet]:
        """List User Sessions Admin"""
        params = {k: v for k, v in locals().items() if k in ['active_only'] and v is not None}
        data = await self._request("GET", f"/admin/users/{user_id}", params=params)
        if isinstance(data, list):
            return [SessionGet.model_validate(item) for item in data]
        return data

    async def delete_session_admin_by_session_id(self, session_id: str, reason: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Revoke Session Admin"""
        data = await self._request("DELETE", f"/admin/{session_id}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def delete_session_admin_user_all(self, user_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Revoke All User Sessions Admin"""
        data = await self._request("DELETE", f"/admin/users/{user_id}/all")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_sessions_admin_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get Session Stats"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", "/admin/stats", params=params)
        if data:
            return Dict[str, Any].model_validate(data)
        return data
