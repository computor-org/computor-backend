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

    async def get_user(self, user_id: Optional[str] = None) -> UserGet:
        """Get Current User Endpoint"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", "", params=params)
        if data:
            return UserGet.model_validate(data)
        return data

    async def post_user_password(self, payload: UserPassword, user_id: Optional[str] = None) -> Any:
        """Set User Password Endpoint"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/password", json=json_data)

    async def get_user_views(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get Course Views For Current User"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", "/views", params=params)
        if isinstance(data, list):
            return [Dict[str, Any].model_validate(item) for item in data]
        return data

    async def get_user_view_by_course_id(self, course_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get Course Views For Current User By Course"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/views/{course_id}", params=params)
        if isinstance(data, list):
            return [Dict[str, Any].model_validate(item) for item in data]
        return data

    async def post_user_cours_validate(self, course_id: str, payload: CourseMemberValidationRequest, user_id: Optional[str] = None) -> CourseMemberReadinessStatus:
        """Validate Current User Course"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/courses/{course_id}/validate", json=json_data)
        if data:
            return CourseMemberReadinessStatus.model_validate(data)
        return data

    async def post_user_cours_register(self, course_id: str, payload: CourseMemberProviderAccountUpdate, user_id: Optional[str] = None) -> CourseMemberReadinessStatus:
        """Register Current User Course Account"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", f"/courses/{course_id}/register", json=json_data)
        if data:
            return CourseMemberReadinessStatus.model_validate(data)
        return data
