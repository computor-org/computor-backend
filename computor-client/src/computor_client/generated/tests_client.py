"""Auto-generated client for /tests endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.results import ResultList
from computor_types.tests import TestCreate

from computor_client.base import BaseEndpointClient


class TestsClient(BaseEndpointClient):
    """Client for /tests endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/tests",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_tests(payload)

    async def post_tests(self, payload: TestCreate) -> ResultList:
        """Create Test Run"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return ResultList.model_validate(data)
        return data

    async def get_test_statu_by_result_id(self, result_id: str) -> Dict[str, Any]:
        """Get Test Status"""
        data = await self._request("GET", f"/status/{result_id}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data
