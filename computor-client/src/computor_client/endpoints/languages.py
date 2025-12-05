"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.languages import (
    LanguageGet,
    LanguageList,
)

from computor_client.http import AsyncHTTPClient


class LanguagesClient:
    """
    Client for languages endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> LanguageGet:
        """Get Languages"""
        response = await self._http.get(f"/languages/{id}", params=kwargs)
        return LanguageGet.model_validate(response.json())

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> List[LanguageList]:
        """List Languages"""
        response = await self._http.get(
            f"/languages",
            params={"skip": skip, "limit": limit, **kwargs},
        )
        data = response.json()
        if isinstance(data, list):
            return [LanguageList.model_validate(item) for item in data]
        return []

