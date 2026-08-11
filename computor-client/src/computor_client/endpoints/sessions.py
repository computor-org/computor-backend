"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.sessions import (
    SessionCreate,
    SessionGet,
    SessionList,
    SessionUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class SessionsClient:
    """
    Client for sessions endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[SessionList]:
        """List Sessions"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[SessionList]:
        """List Sessions (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/sessions", params=params)
        return Page.from_response(response, SessionList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[SessionCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SessionGet:
        """Create Sessions"""
        response = await self._http.post("/sessions", json_data=data, params=kwargs)
        return SessionGet.model_validate(response.json())

    async def get_admin_stats(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Session Stats"""
        response = await self._http.get("/sessions/admin/stats", params=kwargs)
        return response.json()

    async def list_admin_users(
        self,
        user_id: str,
        **kwargs: Any,
    ) -> List[SessionGet]:
        """List User Sessions Admin"""
        response = await self._http.get(f"/sessions/admin/users/{quote_path(user_id)}", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SessionGet.model_validate(item) for item in data]
        return []

    async def delete_admin_users_all(
        self,
        user_id: str,
        **kwargs: Any,
    ) -> None:
        """Revoke All User Sessions Admin"""
        await self._http.delete(f"/sessions/admin/users/{quote_path(user_id)}/all", params=kwargs)
        return

    async def delete_admin(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> None:
        """Revoke Session Admin"""
        await self._http.delete(f"/sessions/admin/{quote_path(session_id)}", params=kwargs)
        return

    async def list_me(
        self,
        **kwargs: Any,
    ) -> List[SessionList]:
        """List My Sessions"""
        response = await self._http.get("/sessions/me", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [SessionList.model_validate(item) for item in data]
        return []

    async def delete_me_all(
        self,
        **kwargs: Any,
    ) -> None:
        """Revoke All My Sessions"""
        await self._http.delete("/sessions/me/all", params=kwargs)
        return

    async def get_me_current(
        self,
        **kwargs: Any,
    ) -> SessionGet:
        """Get Current Session"""
        response = await self._http.get("/sessions/me/current", params=kwargs)
        return SessionGet.model_validate(response.json())

    async def delete_me(
        self,
        session_id: str,
        **kwargs: Any,
    ) -> None:
        """Revoke My Session"""
        await self._http.delete(f"/sessions/me/{quote_path(session_id)}", params=kwargs)
        return

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Sessions"""
        await self._http.delete(f"/sessions/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> SessionGet:
        """Get Sessions"""
        response = await self._http.get(f"/sessions/{quote_path(id)}", params=kwargs)
        return SessionGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[SessionUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> SessionGet:
        """Update Sessions"""
        response = await self._http.patch(f"/sessions/{quote_path(id)}", json_data=data, params=kwargs)
        return SessionGet.model_validate(response.json())

