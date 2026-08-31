"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.documents import (
    DocumentDelete,
    DocumentDirectoryCreate,
    DocumentDirectoryDelete,
    DocumentDirectoryGet,
    DocumentDirectoryRename,
    DocumentGet,
    DocumentList,
    DocumentPermissionsGet,
    DocumentRename,
)

from computor_client.http import AsyncHTTPClient


class DocumentsClient:
    """
    Client for documents endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def delete_directories(
        self,
        data: Union[DocumentDirectoryDelete, Dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        """Delete Document Directory"""
        await self._http.delete("/documents/directories", json_data=data, params=kwargs)
        return

    async def update_directories(
        self,
        data: Union[DocumentDirectoryRename, Dict[str, Any]],
        **kwargs: Any,
    ) -> DocumentDirectoryGet:
        """Rename Document Directory"""
        response = await self._http.patch("/documents/directories", json_data=data, params=kwargs)
        return DocumentDirectoryGet.model_validate(response.json())

    async def directories(
        self,
        data: Union[DocumentDirectoryCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> DocumentDirectoryGet:
        """Create Document Directory"""
        response = await self._http.post("/documents/directories", json_data=data, params=kwargs)
        return DocumentDirectoryGet.model_validate(response.json())

    async def delete_files(
        self,
        data: Union[DocumentDelete, Dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        """Delete Document File"""
        await self._http.delete("/documents/files", json_data=data, params=kwargs)
        return

    async def get_files(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Document File"""
        response = await self._http.get("/documents/files", params=kwargs)
        return response.json()

    async def update_files(
        self,
        data: Union[DocumentRename, Dict[str, Any]],
        **kwargs: Any,
    ) -> DocumentGet:
        """Rename Document File"""
        response = await self._http.patch("/documents/files", json_data=data, params=kwargs)
        return DocumentGet.model_validate(response.json())

    async def files(
        self,
        file: bytes,
        scope: str,
        path: str,
        scope_id: Optional[str] = None,
        **kwargs: Any,
    ) -> DocumentGet:
        """Upload Document File"""
        files = {"file": file}
        form_fields = {k: v for k, v in {"scope": scope, "path": path, "scope_id": scope_id}.items() if v is not None}
        response = await self._http.post("/documents/files", files=files, data=form_fields, params=kwargs)
        return DocumentGet.model_validate(response.json())

    async def list_list(
        self,
        **kwargs: Any,
    ) -> List[DocumentList]:
        """List Documents Directory"""
        response = await self._http.get("/documents/list", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [DocumentList.model_validate(item) for item in data]
        return []

    async def get_permissions(
        self,
        **kwargs: Any,
    ) -> DocumentPermissionsGet:
        """Get Documents Permissions"""
        response = await self._http.get("/documents/permissions", params=kwargs)
        return DocumentPermissionsGet.model_validate(response.json())

