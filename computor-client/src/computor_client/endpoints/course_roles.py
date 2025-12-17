"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

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

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseRoleGet:
        """Get Course-Roles"""
        response = await self._http.get(f"/course-roles/{id}", params=kwargs)
        return CourseRoleGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseRoleList]:
        """List Course-Roles"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/course-roles",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [CourseRoleList.model_validate(item) for item in data]
        return []

