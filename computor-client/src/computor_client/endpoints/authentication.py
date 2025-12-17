"""
Auto-generated endpoint client.

This module is auto-generated from the OpenAPI specification.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from computor_types.auth import (
    LocalLoginRequest,
    LocalLoginResponse,
    LocalTokenRefreshRequest,
    LocalTokenRefreshResponse,
    LogoutResponse,
    ProviderInfo,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserRegistrationRequest,
    UserRegistrationResponse,
)
from computor_types.password_management import (
    AdminResetPasswordRequest,
    AdminSetPasswordRequest,
    ChangePasswordRequest,
    PasswordOperationResponse,
    PasswordStatusResponse,
    SetPasswordRequest,
    UserManagerResetPasswordRequest,
)

from computor_client.http import AsyncHTTPClient


class AuthenticationClient:
    """
    Client for authentication endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def auth_login(
        self,
        data: Union[LocalLoginRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> LocalLoginResponse:
        """Login With Credentials"""
        response = await self._http.post(f"/auth/login", json_data=data, params=kwargs)
        return LocalLoginResponse.model_validate(response.json())

    async def auth_providers(
        self,
        **kwargs: Any,
    ) -> List[ProviderInfo]:
        """List Providers"""
        response = await self._http.get(f"/auth/providers", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ProviderInfo.model_validate(item) for item in data]
        return []

    async def get_auth_login(
        self,
        provider: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Initiate Login"""
        response = await self._http.get(f"/auth/{provider}/login", params=kwargs)
        return response.json()

    async def auth_callback(
        self,
        provider: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Handle Callback"""
        response = await self._http.get(f"/auth/{provider}/callback", params=kwargs)
        return response.json()

    async def auth_success(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Sso Success"""
        response = await self._http.get(f"/auth/success", params=kwargs)
        return response.json()

    async def auth_logout(
        self,
        **kwargs: Any,
    ) -> LogoutResponse:
        """Logout"""
        response = await self._http.post(f"/auth/logout", params=kwargs)
        return LogoutResponse.model_validate(response.json())

    async def auth_admin_plugins(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List All Plugins"""
        response = await self._http.get(f"/auth/admin/plugins", params=kwargs)
        return response.json()

    async def auth_admin_plugins_enable(
        self,
        plugin_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Enable Plugin"""
        response = await self._http.post(f"/auth/admin/plugins/{plugin_name}/enable", params=kwargs)
        return response.json()

    async def auth_admin_plugins_disable(
        self,
        plugin_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Disable Plugin"""
        response = await self._http.post(f"/auth/admin/plugins/{plugin_name}/disable", params=kwargs)
        return response.json()

    async def auth_admin_plugins_reload(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Reload Plugins"""
        response = await self._http.post(f"/auth/admin/plugins/reload", params=kwargs)
        return response.json()

    async def auth_register(
        self,
        data: Union[UserRegistrationRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> UserRegistrationResponse:
        """Register User"""
        response = await self._http.post(f"/auth/register", json_data=data, params=kwargs)
        return UserRegistrationResponse.model_validate(response.json())

    async def auth_refresh_local(
        self,
        data: Union[LocalTokenRefreshRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> LocalTokenRefreshResponse:
        """Refresh Local Token"""
        response = await self._http.post(f"/auth/refresh/local", json_data=data, params=kwargs)
        return LocalTokenRefreshResponse.model_validate(response.json())

    async def auth_refresh(
        self,
        data: Union[TokenRefreshRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> TokenRefreshResponse:
        """Refresh Token"""
        response = await self._http.post(f"/auth/refresh", json_data=data, params=kwargs)
        return TokenRefreshResponse.model_validate(response.json())

    async def password_status(
        self,
        **kwargs: Any,
    ) -> PasswordStatusResponse:
        """Get Password Status"""
        response = await self._http.get(f"/password/status", params=kwargs)
        return PasswordStatusResponse.model_validate(response.json())

    async def password_set(
        self,
        data: Union[SetPasswordRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> PasswordOperationResponse:
        """Set Initial Password"""
        response = await self._http.post(f"/password/set", json_data=data, params=kwargs)
        return PasswordOperationResponse.model_validate(response.json())

    async def password_change(
        self,
        data: Union[ChangePasswordRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> PasswordOperationResponse:
        """Change Password"""
        response = await self._http.post(f"/password/change", json_data=data, params=kwargs)
        return PasswordOperationResponse.model_validate(response.json())

    async def password_admin_set(
        self,
        data: Union[AdminSetPasswordRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> PasswordOperationResponse:
        """Admin Set Password"""
        response = await self._http.post(f"/password/admin/set", json_data=data, params=kwargs)
        return PasswordOperationResponse.model_validate(response.json())

    async def password_admin_reset(
        self,
        data: Union[AdminResetPasswordRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> PasswordOperationResponse:
        """Admin Reset Password"""
        response = await self._http.post(f"/password/admin/reset", json_data=data, params=kwargs)
        return PasswordOperationResponse.model_validate(response.json())

    async def password_reset(
        self,
        data: Union[UserManagerResetPasswordRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> PasswordOperationResponse:
        """User Manager Reset Password"""
        response = await self._http.post(f"/password/reset", json_data=data, params=kwargs)
        return PasswordOperationResponse.model_validate(response.json())

    async def password_admin_status(
        self,
        username: str,
        **kwargs: Any,
    ) -> PasswordStatusResponse:
        """Admin Get User Password Status"""
        response = await self._http.get(f"/password/admin/status/{username}", params=kwargs)
        return PasswordStatusResponse.model_validate(response.json())

