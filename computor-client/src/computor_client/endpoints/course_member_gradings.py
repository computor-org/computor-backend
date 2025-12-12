"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.course_member_gradings import (
    CourseMemberGradingsGet,
    CourseMemberGradingsList,
)

from computor_client.http import AsyncHTTPClient


class CourseMemberGradingsClient:
    """
    Client for course member gradings endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def list(
        self,
        query: Optional[BaseModel] = None,
        **kwargs: Any,
    ) -> List[CourseMemberGradingsList]:
        """List course member grading statistics for a course"""
        params = query.model_dump(exclude_none=True) if query else {}
        params.update(kwargs)
        response = await self._http.get(
            f"/course-member-gradings",
            params=params,
        )
        data = response.json()
        if isinstance(data, list):
            return [CourseMemberGradingsList.model_validate(item) for item in data]
        return []

    async def get(
        self,
        course_member_id: str,
        **kwargs: Any,
    ) -> CourseMemberGradingsGet:
        """Get course member grading statistics"""
        response = await self._http.get(f"/course-member-gradings/{course_member_id}", params=kwargs)
        return CourseMemberGradingsGet.model_validate(response.json())

