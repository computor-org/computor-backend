"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


from computor_client.http import AsyncHTTPClient


class CourseDeploymentClient:
    """
    Client for course deployment endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def course_families_deploy_course(
        self,
        course_family_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Deploy Course"""
        response = await self._http.post(f"/course-families/{course_family_id}/deploy-course", params=kwargs)
        return response.json()

