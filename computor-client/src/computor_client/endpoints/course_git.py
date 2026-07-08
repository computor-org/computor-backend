"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class CourseGitClient:
    """
    Client for course git endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def courses(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Upsert Course Git Binding Endpoint"""
        response = await self._http.put(f"/courses/{course_id}/git", params=kwargs)
        return response.json()

    async def get_courses(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Course Git Binding Endpoint"""
        response = await self._http.get(f"/courses/{course_id}/git", params=kwargs)
        return response.json()

