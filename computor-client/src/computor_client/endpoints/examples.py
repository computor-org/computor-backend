"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.cascade_deletion import (
    ExampleBulkDeleteResult,
    ExampleVersionDeleteResult,
)
from computor_types.example import (
    ExampleDependencyCreate,
    ExampleDependencyGet,
    ExampleDownloadResponse,
    ExampleGet,
    ExampleList,
    ExampleUploadRequest,
    ExampleVersionCreate,
    ExampleVersionGet,
    ExampleVersionList,
)

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class ExamplesClient:
    """
    Client for examples endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[ExampleList]:
        """List Examples"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[ExampleList]:
        """List Examples (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get(f"/examples", params=params)
        return Page.from_response(response, ExampleList, skip=skip, limit=limit)

    async def delete_by_pattern(
        self,
        **kwargs: Any,
    ) -> ExampleBulkDeleteResult:
        """Delete examples by identifier prefix pattern"""
        response = await self._http.delete(f"/examples/by-pattern", params=kwargs)
        return ExampleBulkDeleteResult.model_validate(response.json())

    async def get_download(
        self,
        version_id: str,
        **kwargs: Any,
    ) -> ExampleDownloadResponse:
        """Download Example Version"""
        response = await self._http.get(f"/examples/download/{quote_path(version_id)}", params=kwargs)
        return ExampleDownloadResponse.model_validate(response.json())

    async def upload(
        self,
        data: Union[ExampleUploadRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> ExampleVersionGet:
        """Upload Example"""
        response = await self._http.post(f"/examples/upload", json_data=data, params=kwargs)
        return ExampleVersionGet.model_validate(response.json())

    async def delete_versions(
        self,
        version_id: str,
        **kwargs: Any,
    ) -> ExampleVersionDeleteResult:
        """Delete a single example version"""
        response = await self._http.delete(f"/examples/versions/{quote_path(version_id)}", params=kwargs)
        return ExampleVersionDeleteResult.model_validate(response.json())

    async def get_versions(
        self,
        version_id: str,
        **kwargs: Any,
    ) -> ExampleVersionGet:
        """Get Version"""
        response = await self._http.get(f"/examples/versions/{quote_path(version_id)}", params=kwargs)
        return ExampleVersionGet.model_validate(response.json())

    async def get(
        self,
        example_id: str,
        **kwargs: Any,
    ) -> ExampleGet:
        """Get Example"""
        response = await self._http.get(f"/examples/{quote_path(example_id)}", params=kwargs)
        return ExampleGet.model_validate(response.json())

    async def list_dependencies(
        self,
        example_id: str,
        **kwargs: Any,
    ) -> List[ExampleDependencyGet]:
        """List Dependencies"""
        response = await self._http.get(f"/examples/{quote_path(example_id)}/dependencies", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ExampleDependencyGet.model_validate(item) for item in data]
        return []

    async def dependencies(
        self,
        example_id: str,
        data: Union[ExampleDependencyCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ExampleDependencyGet:
        """Add Dependency"""
        response = await self._http.post(f"/examples/{quote_path(example_id)}/dependencies", json_data=data, params=kwargs)
        return ExampleDependencyGet.model_validate(response.json())

    async def delete_dependencies(
        self,
        example_id: str,
        dependency_id: str,
        **kwargs: Any,
    ) -> None:
        """Remove Dependency"""
        await self._http.delete(f"/examples/{quote_path(example_id)}/dependencies/{quote_path(dependency_id)}", params=kwargs)
        return

    async def get_download_by_example_id(
        self,
        example_id: str,
        **kwargs: Any,
    ) -> ExampleDownloadResponse:
        """Download Example Latest"""
        response = await self._http.get(f"/examples/{quote_path(example_id)}/download", params=kwargs)
        return ExampleDownloadResponse.model_validate(response.json())

    async def list_versions(
        self,
        example_id: str,
        **kwargs: Any,
    ) -> List[ExampleVersionList]:
        """List Versions"""
        response = await self._http.get(f"/examples/{quote_path(example_id)}/versions", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ExampleVersionList.model_validate(item) for item in data]
        return []

    async def versions(
        self,
        example_id: str,
        data: Union[ExampleVersionCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ExampleVersionGet:
        """Create Version"""
        response = await self._http.post(f"/examples/{quote_path(example_id)}/versions", json_data=data, params=kwargs)
        return ExampleVersionGet.model_validate(response.json())

