"""Auto-generated client for /results endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.results import (
    ResultCreate,
    ResultGet,
    ResultList,
    ResultUpdate,
)
from computor_types.tasks import TaskStatus

from computor_client.base import BaseEndpointClient


class ResultsClient(BaseEndpointClient):
    """Client for /results endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/results",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_results(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_results(**params)
        return await self.get_results()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_result_by_result_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_result_by_result_id(id)

    async def get_results(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, submitter_id: Optional[str] = None, course_member_id: Optional[str] = None, course_content_id: Optional[str] = None, course_content_type_id: Optional[str] = None, submission_group_id: Optional[str] = None, submission_artifact_id: Optional[str] = None, execution_backend_id: Optional[str] = None, test_system_id: Optional[str] = None, version_identifier: Optional[str] = None, status: Optional[str] = None, latest: Optional[str] = None, result: Optional[str] = None, grade: Optional[str] = None, result_json: Optional[str] = None) -> List[ResultList]:
        """List Results"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'submitter_id', 'course_member_id', 'course_content_id', 'course_content_type_id', 'submission_group_id', 'submission_artifact_id', 'execution_backend_id', 'test_system_id', 'version_identifier', 'status', 'latest', 'result', 'grade', 'result_json'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [ResultList.model_validate(item) for item in data]
        return data

    async def post_results(self, payload: ResultCreate) -> ResultGet:
        """Create Result"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return ResultGet.model_validate(data)
        return data

    async def get_result_by_result_id(self, result_id: str) -> ResultGet:
        """Get Result"""
        data = await self._request("GET", f"/{result_id}")
        if data:
            return ResultGet.model_validate(data)
        return data

    async def patch_result_by_result_id(self, result_id: str, payload: ResultUpdate) -> ResultGet:
        """Update Result"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{result_id}", json=json_data)
        if data:
            return ResultGet.model_validate(data)
        return data

    async def delete_result_by_result_id(self, result_id: str) -> Any:
        """Delete Result"""
        data = await self._request("DELETE", f"/{result_id}")

    async def get_result_statu(self, result_id: str) -> TaskStatus:
        """Result Status"""
        data = await self._request("GET", f"/{result_id}/status")
        if data:
            return TaskStatus.model_validate(data)
        return data
