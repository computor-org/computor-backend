"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.cascade_deletion import CascadeDeleteResult
from computor_types.course_families import (
    CourseFamilyCreate,
    CourseFamilyGet,
    CourseFamilyList,
    CourseFamilyUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class CourseFamiliesClient:
    """
    Client for course families endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseFamilyList]:
        """List Course-Families"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[CourseFamilyList]:
        """List Course-Families (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/course-families", params=params)
        return Page.from_response(response, CourseFamilyList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[CourseFamilyCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseFamilyGet:
        """Create Course-Families"""
        response = await self._http.post("/course-families", json_data=data, params=kwargs)
        return CourseFamilyGet.model_validate(response.json())

    async def delete(
        self,
        course_family_id: str,
        **kwargs: Any,
    ) -> CascadeDeleteResult:
        """Delete course family and all descendant courses"""
        response = await self._http.delete(f"/course-families/{quote_path(course_family_id)}", params=kwargs)
        return CascadeDeleteResult.model_validate(response.json())

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> CourseFamilyGet:
        """Get Course-Families"""
        response = await self._http.get(f"/course-families/{quote_path(id)}", params=kwargs)
        return CourseFamilyGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[CourseFamilyUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseFamilyGet:
        """Update Course-Families"""
        response = await self._http.patch(f"/course-families/{quote_path(id)}", json_data=data, params=kwargs)
        return CourseFamilyGet.model_validate(response.json())

