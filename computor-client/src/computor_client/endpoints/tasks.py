"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, Union

from computor_types.tasks import (
    TaskInfo,
    TaskResult,
    TaskSubmission,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class TasksClient:
    """
    Client for tasks endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def get(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Tasks"""
        response = await self._http.get("/tasks", params=kwargs)
        return response.json()

    async def submit(
        self,
        data: Union[TaskSubmission, Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Submit Task"""
        response = await self._http.post("/tasks/submit", json_data=data, params=kwargs)
        return response.json()

    async def list_types(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Task Types"""
        response = await self._http.get("/tasks/types", params=kwargs)
        return response.json()

    async def get_workers_status(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Worker Status"""
        response = await self._http.get("/tasks/workers/status", params=kwargs)
        return response.json()

    async def delete(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Task"""
        await self._http.delete(f"/tasks/{quote_path(task_id)}", params=kwargs)
        return

    async def get_by_task_id(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> TaskInfo:
        """Get Task"""
        response = await self._http.get(f"/tasks/{quote_path(task_id)}", params=kwargs)
        return TaskInfo.model_validate(response.json())

    async def delete_cancel(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> None:
        """Cancel Task"""
        await self._http.delete(f"/tasks/{quote_path(task_id)}/cancel", params=kwargs)
        return

    async def get_result(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> TaskResult:
        """Get Task Result"""
        response = await self._http.get(f"/tasks/{quote_path(task_id)}/result", params=kwargs)
        return TaskResult.model_validate(response.json())

    async def get_status(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> TaskInfo:
        """Get Task Status"""
        response = await self._http.get(f"/tasks/{quote_path(task_id)}/status", params=kwargs)
        return TaskInfo.model_validate(response.json())

