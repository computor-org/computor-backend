"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

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

    async def create(
        self,
        data: Union[CourseMemberCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseMemberGet:
        """Create Course-Members"""
        response = await self._http.post(f"/course-members", json_data=data, params=kwargs)
        return CourseMemberGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseMemberList]:
        """List Course-Members"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/course-members",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [CourseMemberList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseMemberGet:
        """Get Course-Members"""
        response = await self._http.get(f"/course-members/{id}", params=kwargs)
        return CourseMemberGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseMemberUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseMemberGet:
        """Update Course-Members"""
        response = await self._http.patch(f"/course-members/{id}", json_data=data, params=kwargs)
        return CourseMemberGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Members"""
        await self._http.delete(f"/course-members/{id}", params=kwargs)
        return

