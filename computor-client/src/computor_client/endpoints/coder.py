"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.tasks import TaskInfo

from computor_client.http import AsyncHTTPClient


class CoderClient:
    """
    Client for coder endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def health(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Check Coder server health"""
        response = await self._http.get(f"/coder/health", params=kwargs)
        return response.json()

    async def templates(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List available workspace templates"""
        response = await self._http.get(f"/coder/templates", params=kwargs)
        return response.json()

    async def workspaces_provision(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Provision a workspace"""
        response = await self._http.post(f"/coder/workspaces/provision", params=kwargs)
        return response.json()

    async def workspaces(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get workspaces"""
        response = await self._http.get(f"/coder/workspaces", params=kwargs)
        return response.json()

    async def workspaces_exists(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Check if user has any workspaces"""
        response = await self._http.get(f"/coder/workspaces/exists", params=kwargs)
        return response.json()

    async def get_workspaces(
        self,
        username: str,
        workspace_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get workspace details"""
        response = await self._http.get(f"/coder/workspaces/{username}/{workspace_name}", params=kwargs)
        return response.json()

    async def delete_workspaces(
        self,
        username: str,
        workspace_name: str,
        **kwargs: Any,
    ) -> None:
        """Delete a workspace"""
        await self._http.delete(f"/coder/workspaces/{username}/{workspace_name}", params=kwargs)
        return

    async def workspaces_start(
        self,
        username: str,
        workspace_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Start a workspace"""
        response = await self._http.post(f"/coder/workspaces/{username}/{workspace_name}/start", params=kwargs)
        return response.json()

    async def workspaces_stop(
        self,
        username: str,
        workspace_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Stop a workspace"""
        response = await self._http.post(f"/coder/workspaces/{username}/{workspace_name}/stop", params=kwargs)
        return response.json()

    async def session(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get a Coder session token"""
        response = await self._http.post(f"/coder/session", params=kwargs)
        return response.json()

    async def admin_images_build(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Build workspace Docker images"""
        response = await self._http.post(f"/coder/admin/images/build", params=kwargs)
        return response.json()

    async def admin_templates_push(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Push Coder templates"""
        response = await self._http.post(f"/coder/admin/templates/push", params=kwargs)
        return response.json()

    async def admin_tasks(
        self,
        workflow_id: str,
        **kwargs: Any,
    ) -> TaskInfo:
        """Get admin task status"""
        response = await self._http.get(f"/coder/admin/tasks/{workflow_id}", params=kwargs)
        return TaskInfo.model_validate(response.json())

