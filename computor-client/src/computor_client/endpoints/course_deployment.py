"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.course_deployment import (
    CourseDeployRequest,
    CourseDeployResult,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class CourseDeploymentClient:
    """
    Client for course deployment endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def course_families_deploy_course(
        self,
        course_family_id: str,
        data: Union[CourseDeployRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseDeployResult:
        """Deploy Course"""
        response = await self._http.post(f"/course-families/{quote_path(course_family_id)}/deploy-course", json_data=data, params=kwargs)
        return CourseDeployResult.model_validate(response.json())

