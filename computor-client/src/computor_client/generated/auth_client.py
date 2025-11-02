"""Auto-generated client for /auth endpoints."""

from typing import Optional, List, Dict, Any
import httpx

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

from computor_client.base import AuthenticationClient


class AuthClient(AuthenticationClient):
    """Client for /auth endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/auth",
        )

    async def post_auth_login(self, payload: LocalLoginRequest, user_id: Optional[str] = None) -> LocalLoginResponse:
        """Login With Credentials"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/login", json=json_data)
        if data:
            return LocalLoginResponse.model_validate(data)
        return data

    async def get_auth_providers(self, ) -> List[ProviderInfo]:
        """List Providers"""
        data = await self._request("GET", "/providers")
        if isinstance(data, list):
            return [ProviderInfo.model_validate(item) for item in data]
        return data

    async def get_auth_login(self, provider: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Initiate Login"""
        params = {k: v for k, v in locals().items() if k in ['redirect_uri'] and v is not None}
        data = await self._request("GET", f"/{provider}/login", params=params)
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_auth_callback(self, provider: str, code: str, state: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle Callback"""
        params = {k: v for k, v in locals().items() if k in ['code', 'state', 'user_id'] and v is not None}
        data = await self._request("GET", f"/{provider}/callback", params=params)
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def get_auth_success(self, ) -> Dict[str, Any]:
        """Sso Success"""
        data = await self._request("GET", "/success")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_auth_logout(self, user_id: Optional[str] = None) -> LogoutResponse:
        """Logout"""
        data = await self._request("POST", "/logout")
        if data:
            return LogoutResponse.model_validate(data)
        return data

    async def get_auth_admin_plugins(self, ) -> Dict[str, Any]:
        """List All Plugins"""
        data = await self._request("GET", "/admin/plugins")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_auth_admin_plugin_enable(self, plugin_name: str) -> Dict[str, Any]:
        """Enable Plugin"""
        data = await self._request("POST", f"/admin/plugins/{plugin_name}/enable")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_auth_admin_plugin_disable(self, plugin_name: str) -> Dict[str, Any]:
        """Disable Plugin"""
        data = await self._request("POST", f"/admin/plugins/{plugin_name}/disable")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_auth_admin_plugins_reload(self, ) -> Dict[str, Any]:
        """Reload Plugins"""
        data = await self._request("POST", "/admin/plugins/reload")
        if data:
            return Dict[str, Any].model_validate(data)
        return data

    async def post_auth_register(self, payload: UserRegistrationRequest, user_id: Optional[str] = None) -> UserRegistrationResponse:
        """Register User"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/register", json=json_data)
        if data:
            return UserRegistrationResponse.model_validate(data)
        return data

    async def post_auth_refresh_local(self, payload: LocalTokenRefreshRequest, user_id: Optional[str] = None) -> LocalTokenRefreshResponse:
        """Refresh Local Token"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/refresh/local", json=json_data)
        if data:
            return LocalTokenRefreshResponse.model_validate(data)
        return data

    async def post_auth_refresh(self, payload: TokenRefreshRequest, user_id: Optional[str] = None) -> TokenRefreshResponse:
        """Refresh Token"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/refresh", json=json_data)
        if data:
            return TokenRefreshResponse.model_validate(data)
        return data
