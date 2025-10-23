"""Auto-generated client for /course-execution-backends endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.course_execution_backends import (
    CourseExecutionBackendCreate,
    CourseExecutionBackendGet,
    CourseExecutionBackendList,
)

from computor_client.base import BaseEndpointClient


class CourseExecutionBackendsClient(BaseEndpointClient):
    """Client for /course-execution-backends endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/course-execution-backends",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_course_execution_backends(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_course_execution_backends(**params)
        return await self.get_course_execution_backends()

    async def post_course_execution_backends(self, payload: CourseExecutionBackendCreate) -> CourseExecutionBackendGet:
        """Create Course Execution Backend"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return CourseExecutionBackendGet.model_validate(data)
        return data

    async def get_course_execution_backends(self, skip: Optional[str] = None, limit: Optional[str] = None, execution_backend_id: Optional[str] = None, course_id: Optional[str] = None) -> List[CourseExecutionBackendList]:
        """List Course Execution Backend"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'execution_backend_id', 'course_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [CourseExecutionBackendList.model_validate(item) for item in data]
        return data
