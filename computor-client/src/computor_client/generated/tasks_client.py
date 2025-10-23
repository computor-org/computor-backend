"""Auto-generated client for /tasks endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.tasks import (
    TaskInfo,
    TaskResult,
    TaskSubmission,
)

from computor_client.base import TaskClient


class TasksClient(TaskClient):
    """Client for /tasks endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/tasks",
        )

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_tasks(**params)
        return await self.get_tasks()

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_task_cancel(id)

    async def get_tasks(self, limit: Optional[str] = None, offset: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """List Tasks"""
        params = {k: v for k, v in locals().items() if k in ['limit', 'offset', 'status'] and v is not None}
        data = await self._request("GET", "", params=params)
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_tasks_submit(self, payload: TaskSubmission) -> Dict[str, Any]:
        """Submit Task"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/submit", json=json_data)
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_task_by_task_id(self, task_id: str) -> TaskInfo:
        """Get Task"""
        data = await self._request("GET", f"/{task_id}")
        if data:
            return TaskInfo.model_validate(data)
        return data

    async def delete_task_by_task_id(self, task_id: str) -> Dict[str, Any]:
        """Delete Task"""
        data = await self._request("DELETE", f"/{task_id}")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_task_statu(self, task_id: str) -> TaskInfo:
        """Get Task Status"""
        data = await self._request("GET", f"/{task_id}/status")
        if data:
            return TaskInfo.model_validate(data)
        return data

    async def get_task_result(self, task_id: str) -> TaskResult:
        """Get Task Result"""
        data = await self._request("GET", f"/{task_id}/result")
        if data:
            return TaskResult.model_validate(data)
        return data

    async def delete_task_cancel(self, task_id: str) -> Dict[str, Any]:
        """Cancel Task"""
        data = await self._request("DELETE", f"/{task_id}/cancel")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_tasks_types(self, ) -> List[Dict[str, Any]]:
        """List Task Types"""
        data = await self._request("GET", "/types")
        if isinstance(data, list):
            return [Dict[str, Any].model_validate(item) for item in data]
        return data

    async def get_tasks_workers_status(self, ) -> Dict[str, Any]:
        """Get Worker Status"""
        data = await self._request("GET", "/workers/status")
        if data:
            return Dict[str, Any].model_validate(data)
        return data
