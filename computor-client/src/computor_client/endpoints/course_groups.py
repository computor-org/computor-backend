"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.course_groups import (
    CourseGroupCreate,
    CourseGroupGet,
    CourseGroupList,
    CourseGroupUpdate,
)

from computor_client.http import AsyncHTTPClient


class CourseGroupsClient:
    """
    Client for course groups endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        data: Union[CourseGroupCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseGroupGet:
        """Create Course-Groups"""
        response = await self._http.post(f"/course-groups", json_data=data, params=kwargs)
        return CourseGroupGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseGroupList]:
        """List Course-Groups"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/course-groups",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [CourseGroupList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseGroupGet:
        """Get Course-Groups"""
        response = await self._http.get(f"/course-groups/{id}", params=kwargs)
        return CourseGroupGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseGroupUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseGroupGet:
        """Update Course-Groups"""
        response = await self._http.patch(f"/course-groups/{id}", json_data=data, params=kwargs)
        return CourseGroupGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Groups"""
        await self._http.delete(f"/course-groups/{id}", params=kwargs)
        return

