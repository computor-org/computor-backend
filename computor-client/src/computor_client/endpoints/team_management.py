"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.team_management import (
    AvailableTeam,
    JoinTeamRequest,
    JoinTeamResponse,
    LeaveTeamResponse,
    TeamCreate,
    TeamResponse,
)

from computor_client.http import AsyncHTTPClient


class TeamManagementClient:
    """
    Client for team management endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def course_contents_submission_groups_my_team(
        self,
        course_content_id: str,
        data: Union[TeamCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> TeamResponse:
        """Create My Team"""
        response = await self._http.post(f"/course-contents/{course_content_id}/submission-groups/my-team", json_data=data, params=kwargs)
        return TeamResponse.model_validate(response.json())

    async def get_course_contents_submission_groups_my_team(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> TeamResponse:
        """Get My Team"""
        response = await self._http.get(f"/course-contents/{course_content_id}/submission-groups/my-team", params=kwargs)
        return TeamResponse.model_validate(response.json())

    async def delete_course_contents_submission_groups_my_team(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> LeaveTeamResponse:
        """Leave My Team"""
        await self._http.delete(f"/course-contents/{course_content_id}/submission-groups/my-team", params=kwargs)
        return

    async def course_contents_submission_groups_available(
        self,
        course_content_id: str,
        **kwargs: Any,
    ) -> List[AvailableTeam]:
        """Get Available Teams"""
        response = await self._http.get(f"/course-contents/{course_content_id}/submission-groups/available", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [AvailableTeam.model_validate(item) for item in data]
        return []

    async def submission_groups_join(
        self,
        submission_group_id: str,
        data: Union[JoinTeamRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> JoinTeamResponse:
        """Join Team"""
        response = await self._http.post(f"/submission-groups/{submission_group_id}/join", json_data=data, params=kwargs)
        return JoinTeamResponse.model_validate(response.json())

