"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.courses import (
    CourseCreate,
    CourseGet,
    CourseList,
    CourseUpdate,
)

from computor_client.http import AsyncHTTPClient


class CoursesClient:
    """
    Client for courses endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        data: Union[CourseCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseGet:
        """Create Courses"""
        response = await self._http.post(f"/courses", json_data=data, params=kwargs)
        return CourseGet.model_validate(response.json())

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> List[CourseList]:
        """List Courses"""
        response = await self._http.get(
            f"/courses",
            params={"skip": skip, "limit": limit, **kwargs},
        )
        data = response.json()
        if isinstance(data, list):
            return [CourseList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseGet:
        """Get Courses"""
        response = await self._http.get(f"/courses/{id}", params=kwargs)
        return CourseGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseGet:
        """Update Courses"""
        response = await self._http.patch(f"/courses/{id}", json_data=data, params=kwargs)
        return CourseGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Courses"""
        await self._http.delete(f"/courses/{id}", params=kwargs)
        return

