"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.course_contents import (
    CourseContentCreate,
    CourseContentGet,
    CourseContentList,
    CourseContentUpdate,
)
from computor_types.deployment import (
    DeploymentSummary,
    DeploymentWithHistory,
)

from computor_client.http import AsyncHTTPClient


class CourseContentsClient:
    """
    Client for course contents endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def course_contents_assign_example(
        self,
        content_id: str,
        **kwargs: Any,
    ) -> DeploymentWithHistory:
        """Assign Example To Content"""
        response = await self._http.post(f"/course-contents/{content_id}/assign-example", params=kwargs)
        return DeploymentWithHistory.model_validate(response.json())

    async def course_contents_example(
        self,
        content_id: str,
        **kwargs: Any,
    ) -> None:
        """Unassign Example From Content"""
        await self._http.delete(f"/course-contents/{content_id}/example", params=kwargs)
        return

    async def course_contents_deployment(
        self,
        content_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Deployment Status With Workflow"""
        response = await self._http.get(f"/course-contents/deployment/{content_id}", params=kwargs)
        return response.json()

    async def course_contents_courses_deployment_summary(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> DeploymentSummary:
        """Get Course Deployment Summary"""
        response = await self._http.get(f"/course-contents/courses/{course_id}/deployment-summary", params=kwargs)
        return DeploymentSummary.model_validate(response.json())

    async def get_course_contents_deployment(
        self,
        content_id: str,
        **kwargs: Any,
    ) -> DeploymentWithHistory:
        """Get Content Deployment"""
        response = await self._http.get(f"/course-contents/{content_id}/deployment", params=kwargs)
        return DeploymentWithHistory.model_validate(response.json())

    async def course_contents(
        self,
        data: Union[CourseContentCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentGet:
        """Create Course-Contents"""
        response = await self._http.post(f"/course-contents", json_data=data, params=kwargs)
        return CourseContentGet.model_validate(response.json())

    async def get_course_contents(
        self,
        **kwargs: Any,
    ) -> List[CourseContentList]:
        """List Course-Contents"""
        response = await self._http.get(f"/course-contents", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseContentList.model_validate(item) for item in data]
        return []

    async def get_course_contents_id(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseContentGet:
        """Get Course-Contents"""
        response = await self._http.get(f"/course-contents/{id}", params=kwargs)
        return CourseContentGet.model_validate(response.json())

    async def patch_course_contents(
        self,
        id: str,
        data: Union[CourseContentUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentGet:
        """Update Course-Contents"""
        response = await self._http.patch(f"/course-contents/{id}", json_data=data, params=kwargs)
        return CourseContentGet.model_validate(response.json())

    async def delete_course_contents(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Contents"""
        await self._http.delete(f"/course-contents/{id}", params=kwargs)
        return

    async def course_contents_archive(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Route Course-Contents"""
        response = await self._http.patch(f"/course-contents/{id}/archive", params=kwargs)
        return

