"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

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

    async def course_content_kinds(
        self,
        data: Union[CourseContentKindCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentKindGet:
        """Create Course-Content-Kinds"""
        response = await self._http.post(f"/course-content-kinds", json_data=data, params=kwargs)
        return CourseContentKindGet.model_validate(response.json())

    async def get_course_content_kinds(
        self,
        **kwargs: Any,
    ) -> List[CourseContentKindList]:
        """List Course-Content-Kinds"""
        response = await self._http.get(f"/course-content-kinds", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseContentKindList.model_validate(item) for item in data]
        return []

    async def get_course_content_kinds_id(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseContentKindGet:
        """Get Course-Content-Kinds"""
        response = await self._http.get(f"/course-content-kinds/{id}", params=kwargs)
        return CourseContentKindGet.model_validate(response.json())

    async def patch_course_content_kinds(
        self,
        id: str,
        data: Union[CourseContentKindUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentKindGet:
        """Update Course-Content-Kinds"""
        response = await self._http.patch(f"/course-content-kinds/{id}", json_data=data, params=kwargs)
        return CourseContentKindGet.model_validate(response.json())

    async def delete_course_content_kinds(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Content-Kinds"""
        await self._http.delete(f"/course-content-kinds/{id}", params=kwargs)
        return

