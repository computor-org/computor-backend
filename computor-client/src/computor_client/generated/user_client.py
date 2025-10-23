"""Auto-generated client for /user endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.course_member_accounts import (
    CourseMemberProviderAccountUpdate,
    CourseMemberReadinessStatus,
    CourseMemberValidationRequest,
)
from computor_types.users import (
    UserGet,
    UserPassword,
)

from computor_client.base import BaseEndpointClient


class UserClient(BaseEndpointClient):
    """Client for /user endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/user",
        )

    async def list(self, query=None):
        """List entities (delegates to generated GET method)."""
        if query:
            params = query.model_dump(mode="json", exclude_unset=True) if hasattr(query, "model_dump") else query
            return await self.get_user(**params)
        return await self.get_user()

    async def get_user(self, ) -> UserGet:
        """Get Current User Endpoint"""
        data = await self._request("GET", "")
        if data:
            return UserGet.model_validate(data)
        return data

    async def post_user_password(self, payload: UserPassword) -> Any:
        """Set User Password Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/password", json=json_data)

    async def get_user_views(self, ) -> List[Dict[str, Any]]:
        """Get Course Views For Current User"""
        data = await self._request("GET", "/views")
        if isinstance(data, list):
            return [Dict[str, Any].model_validate(item) for item in data]
        return data

    async def post_user_cours_validate(self, course_id: str, payload: CourseMemberValidationRequest) -> CourseMemberReadinessStatus:
        """Validate Current User Course"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/courses/{course_id}/validate", json=json_data)
        if data:
            return CourseMemberReadinessStatus.model_validate(data)
        return data

    async def post_user_cours_register(self, course_id: str, payload: CourseMemberProviderAccountUpdate) -> CourseMemberReadinessStatus:
        """Register Current User Course Account"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/courses/{course_id}/register", json=json_data)
        if data:
            return CourseMemberReadinessStatus.model_validate(data)
        return data
