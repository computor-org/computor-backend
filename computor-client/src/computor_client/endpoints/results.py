"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.artifacts import ResultArtifactListItem
from computor_types.results import (
    ResultCreate,
    ResultGet,
    ResultList,
    ResultUpdate,
)
from computor_types.tasks import TaskStatus
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class ResultsClient:
    """
    Client for results endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[ResultList]:
        """List Results"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[ResultList]:
        """List Results (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/results", params=params)
        return Page.from_response(response, ResultList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[ResultCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ResultGet:
        """Create Result"""
        response = await self._http.post("/results", json_data=data, params=kwargs)
        return ResultGet.model_validate(response.json())

    async def delete(
        self,
        result_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Result"""
        await self._http.delete(f"/results/{quote_path(result_id)}", params=kwargs)
        return

    async def get(
        self,
        result_id: str,
        **kwargs: Any,
    ) -> ResultGet:
        """Get Result"""
        response = await self._http.get(f"/results/{quote_path(result_id)}", params=kwargs)
        return ResultGet.model_validate(response.json())

    async def update(
        self,
        result_id: str,
        data: Union[ResultUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ResultGet:
        """Update Result"""
        response = await self._http.patch(f"/results/{quote_path(result_id)}", json_data=data, params=kwargs)
        return ResultGet.model_validate(response.json())

    async def list_artifacts(
        self,
        result_id: str,
        **kwargs: Any,
    ) -> List[ResultArtifactListItem]:
        """List Result Artifacts Endpoint"""
        response = await self._http.get(f"/results/{quote_path(result_id)}/artifacts", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ResultArtifactListItem.model_validate(item) for item in data]
        return []

    async def get_artifacts_download(
        self,
        result_id: str,
        **kwargs: Any,
    ) -> bytes:
        """Download Result Artifacts"""
        response = await self._http.get(f"/results/{quote_path(result_id)}/artifacts/download", params=kwargs)
        return response.content

    async def artifacts_upload(
        self,
        result_id: str,
        file: bytes,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Upload Result Artifacts"""
        files = {"file": file}
        response = await self._http.post(f"/results/{quote_path(result_id)}/artifacts/upload", files=files, params=kwargs)
        return response.json()

    async def get_status(
        self,
        result_id: str,
        **kwargs: Any,
    ) -> TaskStatus:
        """Result Status"""
        response = await self._http.get(f"/results/{quote_path(result_id)}/status", params=kwargs)
        return TaskStatus(response.json())

