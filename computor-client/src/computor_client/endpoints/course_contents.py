"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.course_contents import (
    CourseContentCreate,
    CourseContentGet,
    CourseContentList,
    CourseContentMoveRequest,
    CourseContentUpdate,
)
from computor_types.deployment import (
    DeploymentSummary,
    DeploymentWithHistory,
)

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class CourseContentsClient:
    """
    Client for course contents endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseContentList]:
        """List Course-Contents"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[CourseContentList]:
        """List Course-Contents (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get(f"/course-contents", params=params)
        return Page.from_response(response, CourseContentList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[CourseContentCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentGet:
        """Create Course-Contents"""
        response = await self._http.post(f"/course-contents", json_data=data, params=kwargs)
        return CourseContentGet.model_validate(response.json())

    async def get_courses_deployment_summary(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> DeploymentSummary:
        """Get Course Deployment Summary"""
        response = await self._http.get(f"/course-contents/courses/{quote_path(course_id)}/deployment-summary", params=kwargs)
        return DeploymentSummary.model_validate(response.json())

    async def get_deployment(
        self,
        content_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Deployment Status With Workflow"""
        response = await self._http.get(f"/course-contents/deployment/{quote_path(content_id)}", params=kwargs)
        return response.json()

    async def get_deployment_by_content_id(
        self,
        content_id: str,
        **kwargs: Any,
    ) -> DeploymentWithHistory:
        """Get Content Deployment"""
        response = await self._http.get(f"/course-contents/{quote_path(content_id)}/deployment", params=kwargs)
        return DeploymentWithHistory.model_validate(response.json())

    async def delete_example(
        self,
        content_id: str,
        **kwargs: Any,
    ) -> None:
        """Unassign Example From Content"""
        await self._http.delete(f"/course-contents/{quote_path(content_id)}/example", params=kwargs)
        return

    async def update_move(
        self,
        content_id: str,
        data: Union[CourseContentMoveRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentGet:
        """Move Course Content"""
        response = await self._http.patch(f"/course-contents/{quote_path(content_id)}/move", json_data=data, params=kwargs)
        return CourseContentGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Contents"""
        await self._http.delete(f"/course-contents/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseContentGet:
        """Get Course-Contents"""
        response = await self._http.get(f"/course-contents/{quote_path(id)}", params=kwargs)
        return CourseContentGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseContentUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentGet:
        """Update Course-Contents"""
        response = await self._http.patch(f"/course-contents/{quote_path(id)}", json_data=data, params=kwargs)
        return CourseContentGet.model_validate(response.json())

    async def update_archive(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Route Course-Contents"""
        response = await self._http.patch(f"/course-contents/{quote_path(id)}/archive", params=kwargs)
        return

    async def update_unarchive(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Unarchive Course-Contents"""
        response = await self._http.patch(f"/course-contents/{quote_path(id)}/unarchive", params=kwargs)
        return

