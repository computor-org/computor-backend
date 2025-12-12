"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.tasks import (
    TaskInfo,
    TaskResult,
    TaskSubmission,
)

from computor_client.http import AsyncHTTPClient


class TasksClient:
    """
    Client for tasks endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Tasks"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/tasks",
            params=params,
        )
        return response.json()

    async def submit(
        self,
        data: Union[TaskSubmission, Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Submit Task"""
        response = await self._http.post(f"/tasks/submit", json_data=data, params=kwargs)
        return response.json()

    async def get(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> TaskInfo:
        """Get Task"""
        response = await self._http.get(f"/tasks/{task_id}", params=kwargs)
        return TaskInfo.model_validate(response.json())

    async def delete(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Task"""
        await self._http.delete(f"/tasks/{task_id}", params=kwargs)
        return

    async def status(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> TaskInfo:
        """Get Task Status"""
        response = await self._http.get(f"/tasks/{task_id}/status", params=kwargs)
        return TaskInfo.model_validate(response.json())

    async def result(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> TaskResult:
        """Get Task Result"""
        response = await self._http.get(f"/tasks/{task_id}/result", params=kwargs)
        return TaskResult.model_validate(response.json())

    async def cancel(
        self,
        task_id: str,
        **kwargs: Any,
    ) -> None:
        """Cancel Task"""
        await self._http.delete(f"/tasks/{task_id}/cancel", params=kwargs)
        return

    async def types(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List Task Types"""
        response = await self._http.get(f"/tasks/types", params=kwargs)
        return response.json()

    async def workers_status(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Worker Status"""
        response = await self._http.get(f"/tasks/workers/status", params=kwargs)
        return response.json()

