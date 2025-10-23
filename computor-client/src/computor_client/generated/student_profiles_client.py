"""Auto-generated client for /student-profiles endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.student_profile import (
    StudentProfileCreate,
    StudentProfileGet,
    StudentProfileList,
    StudentProfileUpdate,
)

from computor_client.base import BaseEndpointClient


class StudentProfilesClient(BaseEndpointClient):
    """Client for /student-profiles endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/student-profiles",
        )

    async def create(self, payload):
        """Create a new entity (delegates to generated POST method)."""
        return await self.post_student_profiles(payload)

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_student_profiles(**params)
        return await self.get_student_profiles()

    async def update(self, id: str, payload):
        """Update entity (delegates to generated PATCH method)."""
        return await self.patch_student_profile_by_id(id, payload)

    async def delete(self, id: str):
        """Delete entity (delegates to generated DELETE method)."""
        return await self.delete_student_profile_by_id(id)

    async def get_student_profiles(self, skip: Optional[str] = None, limit: Optional[str] = None, id: Optional[str] = None, student_id: Optional[str] = None, student_email: Optional[str] = None, user_id: Optional[str] = None, organization_id: Optional[str] = None) -> List[StudentProfileList]:
        """List Student Profiles"""
        params = {k: v for k, v in locals().items() if k in ['skip', 'limit', 'id', 'student_id', 'student_email', 'user_id', 'organization_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if isinstance(data, list):
            return [StudentProfileList.model_validate(item) for item in data]
        return data

    async def post_student_profiles(self, payload: StudentProfileCreate) -> StudentProfileGet:
        """Create Student Profile"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "", json=json_data)
        if data:
            return StudentProfileGet.model_validate(data)
        return data

    async def get_student_profile_by_id(self, id: str) -> StudentProfileGet:
        """Get Student Profile"""
        data = await self._request("GET", f"/{id}")
        if data:
            return StudentProfileGet.model_validate(data)
        return data

    async def patch_student_profile_by_id(self, id: str, payload: StudentProfileUpdate) -> StudentProfileGet:
        """Update Student Profile"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("PATCH", f"/{id}", json=json_data)
        if data:
            return StudentProfileGet.model_validate(data)
        return data

    async def delete_student_profile_by_id(self, id: str) -> Any:
        """Delete Student Profile"""
        data = await self._request("DELETE", f"/{id}")
