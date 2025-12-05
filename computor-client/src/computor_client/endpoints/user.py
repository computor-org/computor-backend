"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from computor_types.course_member_accounts import (
    CourseMemberProviderAccountUpdate,
    CourseMemberReadinessStatus,
    CourseMemberValidationRequest,
)
from computor_types.user_roles import (
    UserRoleCreate,
    UserRoleGet,
    UserRoleList,
)
from computor_types.users import (
    UserGet,
    UserPassword,
)

from computor_client.http import AsyncHTTPClient


class UserClient:
    """
    Client for user endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def user_roles(
        self,
        **kwargs: Any,
    ) -> List[UserRoleList]:
        """List User Roles"""
        response = await self._http.get(f"/user-roles", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [UserRoleList.model_validate(item) for item in data]
        return []

    async def post_user_roles(
        self,
        data: Union[UserRoleCreate, Dict[str, Any]],
        **kwargs: Any,
    ) -> UserRoleGet:
        """Create User Role"""
        response = await self._http.post(f"/user-roles", json_data=data, params=kwargs)
        return UserRoleGet.model_validate(response.json())

    async def get_user_roles_users_roles(
        self,
        user_id: str,
        role_id: str,
        **kwargs: Any,
    ) -> UserRoleGet:
        """Get User Role Endpoint"""
        response = await self._http.get(f"/user-roles/users/{user_id}/roles/{role_id}", params=kwargs)
        return UserRoleGet.model_validate(response.json())

    async def delete_user_roles_users_roles(
        self,
        user_id: str,
        role_id: str,
        **kwargs: Any,
    ) -> None:
        """Delete User Role Endpoint"""
        await self._http.delete(f"/user-roles/users/{user_id}/roles/{role_id}", params=kwargs)
        return

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> UserGet:
        """Get Current User Endpoint"""
        response = await self._http.get(
            f"/user",
            params={"skip": skip, "limit": limit, **kwargs},
        )
        return UserGet.model_validate(response.json())

    async def password(
        self,
        data: Union[UserPassword, Dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        """Set User Password Endpoint"""
        response = await self._http.post(f"/user/password", json_data=data, params=kwargs)
        return

    async def views(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Course Views For Current User"""
        response = await self._http.get(f"/user/views", params=kwargs)
        return response.json()

    async def get_views(
        self,
        course_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Get Course Views For Current User By Course"""
        response = await self._http.get(f"/user/views/{course_id}", params=kwargs)
        return response.json()

    async def courses_validate(
        self,
        course_id: str,
        data: Union[CourseMemberValidationRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseMemberReadinessStatus:
        """Validate Current User Course"""
        response = await self._http.post(f"/user/courses/{course_id}/validate", json_data=data, params=kwargs)
        return CourseMemberReadinessStatus.model_validate(response.json())

    async def courses_register(
        self,
        course_id: str,
        data: Union[CourseMemberProviderAccountUpdate, Dict[str, Any]],
        **kwargs: Any,
    ) -> CourseMemberReadinessStatus:
        """Register Current User Course Account"""
        response = await self._http.post(f"/user/courses/{course_id}/register", json_data=data, params=kwargs)
        return CourseMemberReadinessStatus.model_validate(response.json())

