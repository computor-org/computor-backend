"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, Union

from computor_types.course_git import (
    CourseGitBindingGet,
    CourseGitBindingUpsert,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class CourseGitClient:
    """
    Client for course git endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def get_courses(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> CourseGitBindingGet:
        """Get Course Git Binding Endpoint"""
        response = await self._http.get(f"/courses/{quote_path(course_id)}/git", params=kwargs)
        return CourseGitBindingGet.model_validate(response.json())

    async def replace_courses(
        self,
        course_id: str,
        data: Union[CourseGitBindingUpsert, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseGitBindingGet:
        """Upsert Course Git Binding Endpoint"""
        response = await self._http.put(f"/courses/{quote_path(course_id)}/git", json_data=data, params=kwargs)
        return CourseGitBindingGet.model_validate(response.json())

