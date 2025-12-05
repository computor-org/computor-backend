"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.course_roles import (
    CourseRoleGet,
    CourseRoleList,
)

from computor_client.http import AsyncHTTPClient


class CourseRolesClient:
    """
    Client for course roles endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def course_roles(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseRoleGet:
        """Get Course-Roles"""
        response = await self._http.get(f"/course-roles/{id}", params=kwargs)
        return CourseRoleGet.model_validate(response.json())

    async def get_course_roles(
        self,
        **kwargs: Any,
    ) -> List[CourseRoleList]:
        """List Course-Roles"""
        response = await self._http.get(f"/course-roles", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseRoleList.model_validate(item) for item in data]
        return []

