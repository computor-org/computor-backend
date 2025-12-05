"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.course_content_types import (
    CourseContentTypeCreate,
    CourseContentTypeGet,
    CourseContentTypeList,
    CourseContentTypeUpdate,
)

from computor_client.http import AsyncHTTPClient


class CourseContentTypesClient:
    """
    Client for course content types endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def course_content_types(
        self,
        data: Union[CourseContentTypeCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentTypeGet:
        """Create Course-Content-Types"""
        response = await self._http.post(f"/course-content-types", json_data=data, params=kwargs)
        return CourseContentTypeGet.model_validate(response.json())

    async def get_course_content_types(
        self,
        **kwargs: Any,
    ) -> List[CourseContentTypeList]:
        """List Course-Content-Types"""
        response = await self._http.get(f"/course-content-types", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseContentTypeList.model_validate(item) for item in data]
        return []

    async def get_course_content_types_id(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseContentTypeGet:
        """Get Course-Content-Types"""
        response = await self._http.get(f"/course-content-types/{id}", params=kwargs)
        return CourseContentTypeGet.model_validate(response.json())

    async def patch_course_content_types(
        self,
        id: str,
        data: Union[CourseContentTypeUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseContentTypeGet:
        """Update Course-Content-Types"""
        response = await self._http.patch(f"/course-content-types/{id}", json_data=data, params=kwargs)
        return CourseContentTypeGet.model_validate(response.json())

    async def delete_course_content_types(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Content-Types"""
        await self._http.delete(f"/course-content-types/{id}", params=kwargs)
        return

