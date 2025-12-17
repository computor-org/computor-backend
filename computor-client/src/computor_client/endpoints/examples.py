"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

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


class ExamplesClient:
    """
    Client for examples endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[ExampleList]:
        """List Examples"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/examples",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [ExampleList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        example_id: str,
        **kwargs: Any,
    ) -> ExampleGet:
        """Get Example"""
        response = await self._http.get(f"/examples/{example_id}", params=kwargs)
        return ExampleGet.model_validate(response.json())

    async def versions(
        self,
        example_id: str,
        data: Union[ExampleVersionCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ExampleVersionGet:
        """Create Version"""
        response = await self._http.post(f"/examples/{example_id}/versions", json_data=data, params=kwargs)
        return ExampleVersionGet.model_validate(response.json())

    async def get_versions(
        self,
        example_id: str,
        **kwargs: Any,
    ) -> List[ExampleVersionList]:
        """List Versions"""
        response = await self._http.get(f"/examples/{example_id}/versions", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ExampleVersionList.model_validate(item) for item in data]
        return []

    async def get_examples_versions_version_id(
        self,
        version_id: str,
        **kwargs: Any,
    ) -> ExampleVersionGet:
        """Get Version"""
        response = await self._http.get(f"/examples/versions/{version_id}", params=kwargs)
        return ExampleVersionGet.model_validate(response.json())

    async def dependencies(
        self,
        example_id: str,
        data: Union[ExampleDependencyCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ExampleDependencyGet:
        """Create Example Dependency"""
        response = await self._http.post(f"/examples/{example_id}/dependencies", json_data=data, params=kwargs)
        return ExampleDependencyGet.model_validate(response.json())

    async def get_dependencies(
        self,
        example_id: str,
        **kwargs: Any,
    ) -> List[ExampleDependencyGet]:
        """Get Example Dependencies"""
        response = await self._http.get(f"/examples/{example_id}/dependencies", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ExampleDependencyGet.model_validate(item) for item in data]
        return []

    async def delete_dependencies(
        self,
        dependency_id: str,
        **kwargs: Any,
    ) -> None:
        """Remove Dependency"""
        await self._http.delete(f"/examples/dependencies/{dependency_id}", params=kwargs)
        return

    async def upload(
        self,
        data: Union[ExampleUploadRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> ExampleVersionGet:
        """Upload Example"""
        response = await self._http.post(f"/examples/upload", json_data=data, params=kwargs)
        return ExampleVersionGet.model_validate(response.json())

    async def download(
        self,
        example_id: str,
        **kwargs: Any,
    ) -> ExampleDownloadResponse:
        """Download Example Latest"""
        response = await self._http.get(f"/examples/{example_id}/download", params=kwargs)
        return ExampleDownloadResponse.model_validate(response.json())

    async def get_download(
        self,
        version_id: str,
        **kwargs: Any,
    ) -> ExampleDownloadResponse:
        """Download Example Version"""
        response = await self._http.get(f"/examples/download/{version_id}", params=kwargs)
        return ExampleDownloadResponse.model_validate(response.json())

    async def delete_delete_dependencies(
        self,
        example_id: str,
        dependency_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Example Dependency"""
        await self._http.delete(f"/examples/{example_id}/dependencies/{dependency_id}", params=kwargs)
        return

