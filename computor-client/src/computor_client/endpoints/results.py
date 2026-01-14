"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.artifacts import ResultArtifactListItem
from computor_types.results import (
    ResultCreate,
    ResultGet,
    ResultList,
    ResultUpdate,
)
from computor_types.tasks import TaskStatus

from computor_client.http import AsyncHTTPClient


class ResultsClient:
    """
    Client for results endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[ResultList]:
        """List Results"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/results",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [ResultList.model_validate(item) for item in data]
        return []

    async def create(
        self,
        data: Union[ResultCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ResultGet:
        """Create Result"""
        response = await self._http.post(f"/results", json_data=data, params=kwargs)
        return ResultGet.model_validate(response.json())

    async def get(
        self,
        result_id: str,
        **kwargs: Any,
    ) -> ResultGet:
        """Get Result"""
        response = await self._http.get(f"/results/{result_id}", params=kwargs)
        return ResultGet.model_validate(response.json())

    async def update(
        self,
        result_id: str,
        data: Union[ResultUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> ResultGet:
        """Update Result"""
        response = await self._http.patch(f"/results/{result_id}", json_data=data, params=kwargs)
        return ResultGet.model_validate(response.json())

    async def delete(
        self,
        result_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Result"""
        await self._http.delete(f"/results/{result_id}", params=kwargs)
        return

    async def status(
        self,
        result_id: str,
        **kwargs: Any,
    ) -> TaskStatus:
        """Result Status"""
        response = await self._http.get(f"/results/{result_id}/status", params=kwargs)
        return TaskStatus(response.json())

    async def artifacts(
        self,
        result_id: str,
        **kwargs: Any,
    ) -> List[ResultArtifactListItem]:
        """List Result Artifacts Endpoint"""
        response = await self._http.get(f"/results/{result_id}/artifacts", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ResultArtifactListItem.model_validate(item) for item in data]
        return []

    async def artifacts_download(
        self,
        result_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Download Result Artifacts"""
        response = await self._http.get(f"/results/{result_id}/artifacts/download", params=kwargs)
        return response.json()

