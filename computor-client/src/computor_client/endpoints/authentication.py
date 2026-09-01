"""
Auto-generated endpoint client.

DO NOT EDIT: this module is auto-generated from the OpenAPI specification.
Hand edits are silently overwritten on the next regeneration.
Run `bash generate.sh python-client` to regenerate.
"""

from typing import Any, Dict, List, Union

from computor_types.auth import (
    LocalTokenRefreshRequest,
    LocalTokenRefreshResponse,
    LogoutResponse,
    ProviderInfo,
    TokenRefreshRequest,
    TokenRefreshResponse,
)

from computor_client.http import AsyncHTTPClient
from computor_client.urls import quote_path


class AuthenticationClient:
    """
    Client for authentication endpoints.
    """

    def __init__(self, http_client: AsyncHTTPClient) -> None:
        self._http = http_client

    async def get_auth_admin_plugins(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """List All Plugins"""
        response = await self._http.get("/auth/admin/plugins", params=kwargs)
        return response.json()

    async def auth_admin_plugins_reload(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Reload Plugins"""
        response = await self._http.post("/auth/admin/plugins/reload", params=kwargs)
        return response.json()

    async def auth_admin_plugins_disable(
        self,
        plugin_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Disable Plugin"""
        response = await self._http.post(f"/auth/admin/plugins/{quote_path(plugin_name)}/disable", params=kwargs)
        return response.json()

    async def auth_admin_plugins_enable(
        self,
        plugin_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Enable Plugin"""
        response = await self._http.post(f"/auth/admin/plugins/{quote_path(plugin_name)}/enable", params=kwargs)
        return response.json()

    async def get_auth_coder_reauth(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Coder Reauth"""
        response = await self._http.get("/auth/coder-reauth", params=kwargs)
        return response.json()

    async def auth_logout(
        self,
        **kwargs: Any,
    ) -> LogoutResponse:
        """Logout"""
        response = await self._http.post("/auth/logout", params=kwargs)
        return LogoutResponse.model_validate(response.json())

    async def list_auth_providers(
        self,
        **kwargs: Any,
    ) -> List[ProviderInfo]:
        """List Providers"""
        response = await self._http.get("/auth/providers", params=kwargs)
        data = response.json()
        if isinstance(data, list):
            return [ProviderInfo.model_validate(item) for item in data]
        return []

    async def auth_refresh(
        self,
        data: Union[TokenRefreshRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> TokenRefreshResponse:
        """Refresh Token"""
        response = await self._http.post("/auth/refresh", json_data=data, params=kwargs)
        return TokenRefreshResponse.model_validate(response.json())

    async def auth_refresh_local(
        self,
        data: Union[LocalTokenRefreshRequest, Dict[str, Any]],
        **kwargs: Any,
    ) -> LocalTokenRefreshResponse:
        """Refresh Local Token"""
        response = await self._http.post("/auth/refresh/local", json_data=data, params=kwargs)
        return LocalTokenRefreshResponse.model_validate(response.json())

    async def get_auth_success(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Sso Success"""
        response = await self._http.get("/auth/success", params=kwargs)
        return response.json()

    async def get_auth_verify_coder_access(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Verify Coder Access"""
        response = await self._http.get("/auth/verify-coder-access", params=kwargs)
        return response.json()

    async def get_auth_verify_documents_access(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Verify Documents Access"""
        response = await self._http.get("/auth/verify-documents-access", params=kwargs)
        return response.json()

    async def get_auth_workspace_unavailable(
        self,
        owner: str,
        workspace_name: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Workspace Unavailable"""
        response = await self._http.get(f"/auth/workspace-unavailable/{quote_path(owner)}/{quote_path(workspace_name)}", params=kwargs)
        return response.json()

    async def get_auth_callback(
        self,
        provider: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Handle Callback"""
        response = await self._http.get(f"/auth/{quote_path(provider)}/callback", params=kwargs)
        return response.json()

    async def get_auth_login(
        self,
        provider: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Initiate Login"""
        response = await self._http.get(f"/auth/{quote_path(provider)}/login", params=kwargs)
        return response.json()

    async def get_auth_logout(
        self,
        provider: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Sso Logout"""
        response = await self._http.get(f"/auth/{quote_path(provider)}/logout", params=kwargs)
        return response.json()

