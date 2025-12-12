"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

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

    async def assign_example(
        self,
        content_id: str,
        **kwargs: Any,
    ) -> DeploymentWithHistory:
        """Assign Example To Content"""
        response = await self._http.post(f"/course-contents/{content_id}/assign-example", params=kwargs)
        return DeploymentWithHistory.model_validate(response.json())

    async def example(
        self,
        content_id: str,
        **kwargs: Any,
    ) -> None:
        """Unassign Example From Content"""
        await self._http.delete(f"/course-contents/{content_id}/example", params=kwargs)
        return

    async def deployment(
        self,
        content_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Deployment Status With Workflow"""
        response = await self._http.get(f"/course-contents/deployment/{content_id}", params=kwargs)
        return response.json()

    async def courses_deployment_summary(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> DeploymentSummary:
        """Get Course Deployment Summary"""
        response = await self._http.get(f"/course-contents/courses/{course_id}/deployment-summary", params=kwargs)
        return DeploymentSummary.model_validate(response.json())

    async def get_deployment(
        self,
        content_id: str,
        **kwargs: Any,
    ) -> DeploymentWithHistory:
        """Get Content Deployment"""
        response = await self._http.get(f"/course-contents/{content_id}/deployment", params=kwargs)
        return DeploymentWithHistory.model_validate(response.json())

    async def create(
        self,
        data: Union[CourseContentCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentGet:
        """Create Course-Contents"""
        response = await self._http.post(f"/course-contents", json_data=data, params=kwargs)
        return CourseContentGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseContentList]:
        """List Course-Contents"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/course-contents",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [CourseContentList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseContentGet:
        """Get Course-Contents"""
        response = await self._http.get(f"/course-contents/{id}", params=kwargs)
        return CourseContentGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseContentUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentGet:
        """Update Course-Contents"""
        response = await self._http.patch(f"/course-contents/{id}", json_data=data, params=kwargs)
        return CourseContentGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Contents"""
        await self._http.delete(f"/course-contents/{id}", params=kwargs)
        return

    async def archive(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Route Course-Contents"""
        response = await self._http.patch(f"/course-contents/{id}/archive", params=kwargs)
        return

