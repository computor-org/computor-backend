"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.student_profile import (
    StudentProfileCreate,
    StudentProfileGet,
    StudentProfileList,
    StudentProfileUpdate,
)

from computor_client.http import AsyncHTTPClient


class StudentProfilesClient:
    """
    Client for student profiles endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def student_profiles(
        self,
        **kwargs: Any,
    ) -> List[StudentProfileList]:
        """List Student Profiles"""
        response = await self._http.get(f"/student-profiles", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [StudentProfileList.model_validate(item) for item in data]
        return []

    async def post_student_profiles(
        self,
        data: Union[StudentProfileCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> StudentProfileGet:
        """Create Student Profile"""
        response = await self._http.post(f"/student-profiles", json_data=data, params=kwargs)
        return StudentProfileGet.model_validate(response.json())

    async def get_student_profiles(
        self,
        id: str,
        **kwargs: Any,
    ) -> StudentProfileGet:
        """Get Student Profile"""
        response = await self._http.get(f"/student-profiles/{id}", params=kwargs)
        return StudentProfileGet.model_validate(response.json())

    async def patch_student_profiles(
        self,
        id: str,
        data: Union[StudentProfileUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> StudentProfileGet:
        """Update Student Profile"""
        response = await self._http.patch(f"/student-profiles/{id}", json_data=data, params=kwargs)
        return StudentProfileGet.model_validate(response.json())

    async def delete_student_profiles(
        self,
        id: str,
        **kwargs: Any,
    ) -> None:
        """Delete Student Profile"""
        await self._http.delete(f"/student-profiles/{id}", params=kwargs)
        return

