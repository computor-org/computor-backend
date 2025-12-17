"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.course_member_import import (
    CourseMemberImportRequest,
    CourseMemberImportResponse,
)

from computor_client.http import AsyncHTTPClient


class CourseMemberImportClient:
    """
    Client for course member import endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def post(
        self,
        course_id: str,
        data: Union[CourseMemberImportRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseMemberImportResponse:
        """Import Member"""
        response = await self._http.post(f"/course-member-import/{course_id}", json_data=data, params=kwargs)
        return CourseMemberImportResponse.model_validate(response.json())

