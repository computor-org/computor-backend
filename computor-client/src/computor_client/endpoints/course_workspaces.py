"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.coder import WorkspaceActionResponse
from computor_types.course_workspaces import (
    CourseStudentWorkspacesResponse,
    CourseWorkspaceSettingsGet,
    CourseWorkspaceSettingsUpdate,
    StudentWorkspaceProvisionRequest,
    StudentWorkspaceProvisionResponse,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class CourseWorkspacesClient:
    """
    Client for course workspaces endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def get_courses_student_workspaces(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> CourseStudentWorkspacesResponse:
        """List Student Workspaces Endpoint"""
        response = await self._http.get(f"/courses/{quote_path(course_id)}/student-workspaces", params=kwargs)
        return CourseStudentWorkspacesResponse.model_validate(response.json())

    async def courses_student_workspaces_provision(
        self,
        course_id: str,
        data: Union[StudentWorkspaceProvisionRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> StudentWorkspaceProvisionResponse:
        """Provision Student Workspaces Endpoint"""
        response = await self._http.post(f"/courses/{quote_path(course_id)}/student-workspaces/provision", json_data=data, params=kwargs)
        return StudentWorkspaceProvisionResponse.model_validate(response.json())

    async def delete_courses_student_workspaces(
        self,
        course_id: str,
        username: str,
        workspace_name: str,
        **kwargs: Any,
    ) -> WorkspaceActionResponse:
        """Delete Student Workspace Endpoint"""
        response = await self._http.delete(f"/courses/{quote_path(course_id)}/student-workspaces/{quote_path(username)}/{quote_path(workspace_name)}", params=kwargs)
        return WorkspaceActionResponse.model_validate(response.json())

    async def get_courses_workspace_settings(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> CourseWorkspaceSettingsGet:
        """Get Course Workspace Settings Endpoint"""
        response = await self._http.get(f"/courses/{quote_path(course_id)}/workspace-settings", params=kwargs)
        return CourseWorkspaceSettingsGet.model_validate(response.json())

    async def replace_courses_workspace_settings(
        self,
        course_id: str,
        data: Union[CourseWorkspaceSettingsUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseWorkspaceSettingsGet:
        """Update Course Workspace Settings Endpoint"""
        response = await self._http.put(f"/courses/{quote_path(course_id)}/workspace-settings", json_data=data, params=kwargs)
        return CourseWorkspaceSettingsGet.model_validate(response.json())

    async def courses_workspace_settings_apply_policy(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> StudentWorkspaceProvisionResponse:
        """Apply Course Workspace Policy Endpoint"""
        response = await self._http.post(f"/courses/{quote_path(course_id)}/workspace-settings/apply-policy", params=kwargs)
        return StudentWorkspaceProvisionResponse.model_validate(response.json())

