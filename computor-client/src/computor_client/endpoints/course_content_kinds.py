"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.course_content_kind import (
    CourseContentKindCreate,
    CourseContentKindGet,
    CourseContentKindList,
    CourseContentKindUpdate,
)

from computor_client.http import AsyncHTTPClient


class CourseContentKindsClient:
    """
    Client for course content kinds endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def create(
        self,
        data: Union[CourseContentKindCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentKindGet:
        """Create Course-Content-Kinds"""
        response = await self._http.post(f"/course-content-kinds", json_data=data, params=kwargs)
        return CourseContentKindGet.model_validate(response.json())

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseContentKindList]:
        """List Course-Content-Kinds"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/course-content-kinds",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [CourseContentKindList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseContentKindGet:
        """Get Course-Content-Kinds"""
        response = await self._http.get(f"/course-content-kinds/{id}", params=kwargs)
        return CourseContentKindGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseContentKindUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentKindGet:
        """Update Course-Content-Kinds"""
        response = await self._http.patch(f"/course-content-kinds/{id}", json_data=data, params=kwargs)
        return CourseContentKindGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Content-Kinds"""
        await self._http.delete(f"/course-content-kinds/{id}", params=kwargs)
        return

