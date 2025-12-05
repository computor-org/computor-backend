"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.course_members import (
    CourseMemberCreate,
    CourseMemberGet,
    CourseMemberList,
    CourseMemberUpdate,
)

from computor_client.http import AsyncHTTPClient


class CourseMembersClient:
    """
    Client for course members endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def course_members(
        self,
        data: Union[CourseMemberCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseMemberGet:
        """Create Course-Members"""
        response = await self._http.post(f"/course-members", json_data=data, params=kwargs)
        return CourseMemberGet.model_validate(response.json())

    async def get_course_members(
        self,
        **kwargs: Any,
    ) -> List[CourseMemberList]:
        """List Course-Members"""
        response = await self._http.get(f"/course-members", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseMemberList.model_validate(item) for item in data]
        return []

    async def get_course_members_id(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseMemberGet:
        """Get Course-Members"""
        response = await self._http.get(f"/course-members/{id}", params=kwargs)
        return CourseMemberGet.model_validate(response.json())

    async def patch_course_members(
        self,
        id: str,
        data: Union[CourseMemberUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseMemberGet:
        """Update Course-Members"""
        response = await self._http.patch(f"/course-members/{id}", json_data=data, params=kwargs)
        return CourseMemberGet.model_validate(response.json())

    async def delete_course_members(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Members"""
        await self._http.delete(f"/course-members/{id}", params=kwargs)
        return

