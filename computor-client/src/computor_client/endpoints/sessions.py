"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.sessions import (
    SessionCreate,
    SessionGet,
    SessionList,
    SessionUpdate,
)

from computor_client.http import AsyncHTTPClient


class SessionsClient:
    """
    Client for sessions endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        data: Union[SessionCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SessionGet:
        """Create Sessions"""
        response = await self._http.post(f"/sessions", json_data=data, params=kwargs)
        return SessionGet.model_validate(response.json())

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> List[SessionList]:
        """List Sessions"""
        response = await self._http.get(
            f"/sessions",
            params={"skip": skip, "limit": limit, **kwargs},
        )
        data = response.json()
        if isinstance(data, list):
            return [SessionList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> SessionGet:
        """Get Sessions"""
        response = await self._http.get(f"/sessions/{id}", params=kwargs)
        return SessionGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[SessionUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SessionGet:
        """Update Sessions"""
        response = await self._http.patch(f"/sessions/{id}", json_data=data, params=kwargs)
        return SessionGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Sessions"""
        await self._http.delete(f"/sessions/{id}", params=kwargs)
        return

    async def me(
        self,
        **kwargs: Any,
    ) -> List[SessionList]:
        """List My Sessions"""
        response = await self._http.get(f"/sessions/me", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SessionList.model_validate(item) for item in data]
        return []

    async def me_current(
        self,
        **kwargs: Any,
    ) -> SessionGet:
        """Get Current Session"""
        response = await self._http.get(f"/sessions/me/current", params=kwargs)
        return SessionGet.model_validate(response.json())

    async def delete_me(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> None:
        """Revoke My Session"""
        await self._http.delete(f"/sessions/me/{session_id}", params=kwargs)
        return

    async def me_all(
        self,
        **kwargs: Any,
    ) -> None:
        """Revoke All My Sessions"""
        await self._http.delete(f"/sessions/me/all", params=kwargs)
        return

    async def admin_users(
        self,
        user_id: str,
        **kwargs: Any,
    ) -> List[SessionGet]:
        """List User Sessions Admin"""
        response = await self._http.get(f"/sessions/admin/users/{user_id}", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SessionGet.model_validate(item) for item in data]
        return []

    async def admin(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> None:
        """Revoke Session Admin"""
        await self._http.delete(f"/sessions/admin/{session_id}", params=kwargs)
        return

    async def admin_users_all(
        self,
        user_id: str,
        **kwargs: Any,
    ) -> None:
        """Revoke All User Sessions Admin"""
        await self._http.delete(f"/sessions/admin/users/{user_id}/all", params=kwargs)
        return

    async def admin_stats(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Session Stats"""
        response = await self._http.get(f"/sessions/admin/stats", params=kwargs)
        return response.json()

