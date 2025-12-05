"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.course_families import (
    CourseFamilyCreate,
    CourseFamilyGet,
    CourseFamilyList,
    CourseFamilyUpdate,
)

from computor_client.http import AsyncHTTPClient


class CourseFamiliesClient:
    """
    Client for course families endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def course_families(
        self,
        data: Union[CourseFamilyCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseFamilyGet:
        """Create Course-Families"""
        response = await self._http.post(f"/course-families", json_data=data, params=kwargs)
        return CourseFamilyGet.model_validate(response.json())

    async def get_course_families(
        self,
        **kwargs: Any,
    ) -> List[CourseFamilyList]:
        """List Course-Families"""
        response = await self._http.get(f"/course-families", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [CourseFamilyList.model_validate(item) for item in data]
        return []

    async def get_course_families_id(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseFamilyGet:
        """Get Course-Families"""
        response = await self._http.get(f"/course-families/{id}", params=kwargs)
        return CourseFamilyGet.model_validate(response.json())

    async def patch_course_families(
        self,
        id: str,
        data: Union[CourseFamilyUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseFamilyGet:
        """Update Course-Families"""
        response = await self._http.patch(f"/course-families/{id}", json_data=data, params=kwargs)
        return CourseFamilyGet.model_validate(response.json())

    async def delete_course_families(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Course-Families"""
        await self._http.delete(f"/course-families/{id}", params=kwargs)
        return

