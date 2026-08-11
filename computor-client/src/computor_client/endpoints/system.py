"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, Union

from computor_types.maintenance import (
    MaintenanceActivate,
    MaintenanceSchedule,
    MaintenanceStatusGet,
)
from computor_types.system import (
    CourseTaskRequest,
    GenerateAssignmentsRequest,
    GenerateAssignmentsResponse,
    GenerateTemplateRequest,
    GenerateTemplateResponse,
    TaskResponse,
)
from computor_types.update import (
    SystemUpdateScheduleRequest,
    SystemUpdateScheduleResponse,
    SystemUpdateStatusGet,
    SystemUpdateTriggerResponse,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class SystemClient:
    """
    Client for system endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def courses_generate_assignments(
        self,
        course_id: str,
        data: Union[GenerateAssignmentsRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> GenerateAssignmentsResponse:
        """Generate Assignments"""
        response = await self._http.post(f"/system/courses/{quote_path(course_id)}/generate-assignments", json_data=data, params=kwargs)
        return GenerateAssignmentsResponse.model_validate(response.json())

    async def courses_generate_student_template(
        self,
        course_id: str,
        data: Union[GenerateTemplateRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> GenerateTemplateResponse:
        """Generate Student Template"""
        response = await self._http.post(f"/system/courses/{quote_path(course_id)}/generate-student-template", json_data=data, params=kwargs)
        return GenerateTemplateResponse.model_validate(response.json())

    async def get_courses_gitlab_status(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Course Gitlab Status"""
        response = await self._http.get(f"/system/courses/{quote_path(course_id)}/gitlab-status", params=kwargs)
        return response.json()

    async def deploy_courses(
        self,
        data: Union[CourseTaskRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> TaskResponse:
        """Create Course Async"""
        response = await self._http.post("/system/deploy/courses", json_data=data, params=kwargs)
        return TaskResponse.model_validate(response.json())

    async def hierarchy_create(
        self,
        data: Dict[str, Any],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create Hierarchy"""
        response = await self._http.post("/system/hierarchy/create", json_data=data, params=kwargs)
        return response.json()

    async def get_hierarchy_status(
        self,
        workflow_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Hierarchy Status"""
        response = await self._http.get(f"/system/hierarchy/status/{quote_path(workflow_id)}", params=kwargs)
        return response.json()

    async def maintenance_activate(
        self,
        data: Union[MaintenanceActivate, Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Activate Maintenance"""
        response = await self._http.post("/system/maintenance/activate", json_data=data, params=kwargs)
        return response.json()

    async def maintenance_deactivate(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Deactivate Maintenance"""
        response = await self._http.post("/system/maintenance/deactivate", params=kwargs)
        return response.json()

    async def delete_maintenance_schedule(
        self,
        **kwargs: Any,
    ) -> None:
        """Cancel Scheduled Maintenance"""
        await self._http.delete("/system/maintenance/schedule", params=kwargs)
        return

    async def maintenance_schedule(
        self,
        data: Union[MaintenanceSchedule, Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Schedule Maintenance"""
        response = await self._http.post("/system/maintenance/schedule", json_data=data, params=kwargs)
        return response.json()

    async def get_maintenance_status(
        self,
        **kwargs: Any,
    ) -> MaintenanceStatusGet:
        """Get Maintenance Status"""
        response = await self._http.get("/system/maintenance/status", params=kwargs)
        return MaintenanceStatusGet.model_validate(response.json())

    async def update(
        self,
        **kwargs: Any,
    ) -> SystemUpdateTriggerResponse:
        """Trigger Update"""
        response = await self._http.post("/system/update", params=kwargs)
        return SystemUpdateTriggerResponse.model_validate(response.json())

    async def update_check(
        self,
        **kwargs: Any,
    ) -> SystemUpdateStatusGet:
        """Check For Update"""
        response = await self._http.post("/system/update/check", params=kwargs)
        return SystemUpdateStatusGet.model_validate(response.json())

    async def update_reset(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Reset Update State"""
        response = await self._http.post("/system/update/reset", params=kwargs)
        return response.json()

    async def delete_update_schedule(
        self,
        **kwargs: Any,
    ) -> None:
        """Cancel Scheduled Update"""
        await self._http.delete("/system/update/schedule", params=kwargs)
        return

    async def update_schedule(
        self,
        data: Union[SystemUpdateScheduleRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> SystemUpdateScheduleResponse:
        """Schedule Update"""
        response = await self._http.post("/system/update/schedule", json_data=data, params=kwargs)
        return SystemUpdateScheduleResponse.model_validate(response.json())

    async def get_update_status(
        self,
        **kwargs: Any,
    ) -> SystemUpdateStatusGet:
        """Get Update Status"""
        response = await self._http.get("/system/update/status", params=kwargs)
        return SystemUpdateStatusGet.model_validate(response.json())

