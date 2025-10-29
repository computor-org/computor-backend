"""Auto-generated client for /languages endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.languages import (
    LanguageGet,
    LanguageList,
)

from computor_client.base import BaseEndpointClient


class LanguagesClient(BaseEndpointClient):
    """Client for /languages endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/languages",
        )

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_languages(**params)
        return await self.get_languages()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_language_by_id(id)

    async def get_language_by_id(self, id: str, user_id: Optional[str] = None) -> LanguageGet:
        """Get Languages"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{id}", params=params)
        if data:
            return LanguageGet.model_validate(data)
        return data

    async def get_languages(self, skip: Optional[str] = None, limit: Optional[str] = None, code: Optional[str] = None, name: Optional[str] = None, native_name: Optional[str] = None, user_id: Optional[str] = None) -> List[LanguageList]:
        """List Languages"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'code', 'name', 'native_name', 'user_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [LanguageList.model_validate(item) for item in data]
        return data
