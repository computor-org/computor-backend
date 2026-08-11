"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.student_profile import (
    StudentProfileCreate,
    StudentProfileGet,
    StudentProfileList,
    StudentProfileUpdate,
)
from pydantic import BaseModel

from computor_client.http import AsyncHTTPClient
from computor_client.pagination import Page
from computor_client.urls import quote_path


class StudentProfilesClient:
    """
    Client for student profiles endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[StudentProfileList]:
        """List Student Profiles"""
        page = await self.list_page(skip=skip, limit=limit, query=query, **kwargs)
        return page.items

    async def list_page(
        self,
        skip: int = 0,
        limit: int = 100,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> Page[StudentProfileList]:
        """List Student Profiles (one page, with the total row count)."""
        params = query.model_dump(mode="json", exclude_none=True) if query else {}
        params.update({"skip": skip, "limit": limit})
        params.update(kwargs)
        response = await self._http.get("/student-profiles", params=params)
        return Page.from_response(response, StudentProfileList, skip=skip, limit=limit)

    async def create(
        self,
        data: Union[StudentProfileCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> StudentProfileGet:
        """Create Student Profile"""
        response = await self._http.post("/student-profiles", json_data=data, params=kwargs)
        return StudentProfileGet.model_validate(response.json())

    async def delete(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Student Profile"""
        await self._http.delete(f"/student-profiles/{quote_path(id)}", params=kwargs)
        return

    async def get(
        self,
        id: str,
        **kwargs: Any,
    ) -> StudentProfileGet:
        """Get Student Profile"""
        response = await self._http.get(f"/student-profiles/{quote_path(id)}", params=kwargs)
        return StudentProfileGet.model_validate(response.json())

    async def update(
        self,
        id: str,
        data: Union[StudentProfileUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> StudentProfileGet:
        """Update Student Profile"""
        response = await self._http.patch(f"/student-profiles/{quote_path(id)}", json_data=data, params=kwargs)
        return StudentProfileGet.model_validate(response.json())

