"""Auto-generated client for /examples endpoints."""

from typing import Optional, List, Dict, Any
import httpx

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

from computor_client.base import FileOperationClient


class ExamplesClient(FileOperationClient):
    """Client for /examples endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/examples",
        )

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_examples(**params)
        return await self.get_examples()

    async def get(self, id: str):
        """Get entity by ID (delegates to generated GET method)."""
        return await self.get_example_by_example_id(id)

    async def get_examples(self, user_id: Optional[str] = None, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, repository_id: Optional[str] = None, identifier: Optional[str] = None, title: Optional[str] = None, category: Optional[str] = None, search: Optional[str] = None) -> List[ExampleList]:
        """List Examples"""
        params = {k: v for k, v in locals().items() if k in ['user_id', 'skip', 'limit', 'id', 'repository_id', 'identifier', 'title', 'category', 'search'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [ExampleList.model_validate(item) for item in data]
        return data

    async def get_example_by_example_id(self, example_id: str, user_id: Optional[str] = None) -> ExampleGet:
        """Get Example"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{example_id}", params=params)
        if data:
            return ExampleGet.model_validate(data)
        return data

    async def post_example_version(self, example_id: str, payload: ExampleVersionCreate, user_id: Optional[str] = None) -> ExampleVersionGet:
        """Create Version"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/{example_id}/versions", json=json_data)
        if data:
            return ExampleVersionGet.model_validate(data)
        return data

    async def get_example_version(self, example_id: str, skip: Optional[str] = None, limit: Optional[str] = None, version_tag: Optional[str] = None, user_id: Optional[str] = None) -> List[ExampleVersionList]:
        """List Versions"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'version_tag', 'user_id'] and v is not None}
        data = await self._request("GET", f"/{example_id}/versions", params=params)
        if isinstance(data, list):
            return [ExampleVersionList.model_validate(item) for item in data]
        return data

    async def get_example_version_by_version_id(self, version_id: str, user_id: Optional[str] = None) -> ExampleVersionGet:
        """Get Version"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/versions/{version_id}", params=params)
        if data:
            return ExampleVersionGet.model_validate(data)
        return data

    async def post_example_dependency(self, example_id: str, payload: ExampleDependencyCreate, user_id: Optional[str] = None) -> ExampleDependencyGet:
        """Create Example Dependency"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/{example_id}/dependencies", json=json_data)
        if data:
            return ExampleDependencyGet.model_validate(data)
        return data

    async def get_example_dependency(self, example_id: str, user_id: Optional[str] = None) -> List[ExampleDependencyGet]:
        """Get Example Dependencies"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/{example_id}/dependencies", params=params)
        if isinstance(data, list):
            return [ExampleDependencyGet.model_validate(item) for item in data]
        return data

    async def delete_example_dependency_by_dependency_id(self, dependency_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Remove Dependency"""
        data = await self._request("DELETE", f"/dependencies/{dependency_id}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_examples_upload(self, payload: ExampleUploadRequest, user_id: Optional[str] = None) -> ExampleVersionGet:
        """Upload Example"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/upload", json=json_data)
        if data:
            return ExampleVersionGet.model_validate(data)
        return data

    async def get_example_download(self, example_id: str, with_dependencies: Optional[str] = None, user_id: Optional[str] = None) -> ExampleDownloadResponse:
        """Download Example Latest"""
        params = {k: v for k, v in locals().items() if k in ['with_dependencies', 'user_id'] and v is not None}
        data = await self._request("GET", f"/{example_id}/download", params=params)
        if data:
            return ExampleDownloadResponse.model_validate(data)
        return data

    async def get_example_download_by_version_id(self, version_id: str, with_dependencies: Optional[str] = None, user_id: Optional[str] = None) -> ExampleDownloadResponse:
        """Download Example Version"""
        params = {k: v for k, v in locals().items() if k in ['with_dependencies', 'user_id'] and v is not None}
        data = await self._request("GET", f"/download/{version_id}", params=params)
        if data:
            return ExampleDownloadResponse.model_validate(data)
        return data

    async def delete_example_dependency_by_dependency_id(self, example_id: str, dependency_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Delete Example Dependency"""
        data = await self._request("DELETE", f"/{example_id}/dependencies/{dependency_id}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data
