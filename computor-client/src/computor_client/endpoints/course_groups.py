"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

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

    async def course_groups(
        self,
        data: Union[CourseGroupCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseGroupGet:
        """Create Course-Groups"""
        response = await self._http.post(f"/course-groups", json_data=data, params=kwargs)
        return CourseGroupGet.model_validate(response.json())

    async def get_course_groups(
        self,
        **kwargs: Any,
    ) -> List[CourseGroupList]:
        """List Course-Groups"""
        response = await self._http.get(f"/course-groups", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseGroupList.model_validate(item) for item in data]
        return []

    async def get_course_groups_id(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseGroupGet:
        """Get Course-Groups"""
        response = await self._http.get(f"/course-groups/{id}", params=kwargs)
        return CourseGroupGet.model_validate(response.json())

    async def patch_course_groups(
        self,
        id: str,
        data: Union[CourseGroupUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseGroupGet:
        """Update Course-Groups"""
        response = await self._http.patch(f"/course-groups/{id}", json_data=data, params=kwargs)
        return CourseGroupGet.model_validate(response.json())

    async def delete_course_groups(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Groups"""
        await self._http.delete(f"/course-groups/{id}", params=kwargs)
        return

