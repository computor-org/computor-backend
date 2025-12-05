"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.example import (
    ExampleRepositoryCreate,
    ExampleRepositoryGet,
    ExampleRepositoryList,
    ExampleRepositoryUpdate,
)

from computor_client.http import AsyncHTTPClient


class ExampleRepositoriesClient:
    """
    Client for example repositories endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def example_repositories(
        self,
        data: Union[ExampleRepositoryCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ExampleRepositoryGet:
        """Create Example-Repositories"""
        response = await self._http.post(f"/example-repositories", json_data=data, params=kwargs)
        return ExampleRepositoryGet.model_validate(response.json())

    async def get_example_repositories(
        self,
        **kwargs: Any,
    ) -> List[ExampleRepositoryList]:
        """List Example-Repositories"""
        response = await self._http.get(f"/example-repositories", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ExampleRepositoryList.model_validate(item) for item in data]
        return []

    async def get_example_repositories_id(
        self,
        id: str,
        **kwargs: Any,
    ) -> ExampleRepositoryGet:
        """Get Example-Repositories"""
        response = await self._http.get(f"/example-repositories/{id}", params=kwargs)
        return ExampleRepositoryGet.model_validate(response.json())

    async def patch_example_repositories(
        self,
        id: str,
        data: Union[ExampleRepositoryUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ExampleRepositoryGet:
        """Update Example-Repositories"""
        response = await self._http.patch(f"/example-repositories/{id}", json_data=data, params=kwargs)
        return ExampleRepositoryGet.model_validate(response.json())

    async def delete_example_repositories(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Example-Repositories"""
        await self._http.delete(f"/example-repositories/{id}", params=kwargs)
        return

