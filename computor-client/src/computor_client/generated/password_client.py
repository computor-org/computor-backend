"""Auto-generated client for /password endpoints."""

from typing import Optional, List, Dict, Any
import httpx

from computor_types.password_management import (
    AdminResetPasswordRequest,
    AdminSetPasswordRequest,
    ChangePasswordRequest,
    PasswordOperationResponse,
    PasswordStatusResponse,
    SetPasswordRequest,
)

from computor_client.base import BaseEndpointClient


class PasswordClient(BaseEndpointClient):
    """Client for /password endpoints."""

    def __init__(self, client: httpx.AsyncClient):
        super().__init__(
            client=client,
            base_path="/password",
        )

    async def get_password_status(self, user_id: Optional[str] = None) -> PasswordStatusResponse:
        """Get Password Status"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", "/status", params=params)
        if data:
            return PasswordStatusResponse.model_validate(data)
        return data

    async def post_password_set(self, payload: SetPasswordRequest, user_id: Optional[str] = None) -> PasswordOperationResponse:
        """Set Initial Password"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/set", json=json_data)
        if data:
            return PasswordOperationResponse.model_validate(data)
        return data

    async def post_password_change(self, payload: ChangePasswordRequest, user_id: Optional[str] = None) -> PasswordOperationResponse:
        """Change Password"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/change", json=json_data)
        if data:
            return PasswordOperationResponse.model_validate(data)
        return data

    async def post_password_admin_set(self, payload: AdminSetPasswordRequest, user_id: Optional[str] = None) -> PasswordOperationResponse:
        """Admin Set Password"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/admin/set", json=json_data)
        if data:
            return PasswordOperationResponse.model_validate(data)
        return data

    async def post_password_admin_reset(self, payload: AdminResetPasswordRequest, user_id: Optional[str] = None) -> PasswordOperationResponse:
        """Admin Reset Password"""
        json_data = payload.model_dump(mode="json", exclude_unset=True) if hasattr(payload, "model_dump") else payload
        data = await self._request("POST", "/admin/reset", json=json_data)
        if data:
            return PasswordOperationResponse.model_validate(data)
        return data

    async def get_password_admin_statu_by_username(self, username: str, user_id: Optional[str] = None) -> PasswordStatusResponse:
        """Admin Get User Password Status"""
        params = {k: v for k, v in locals().items() if k in ['user_id'] and v is not None}
        data = await self._request("GET", f"/admin/status/{username}", params=params)
        if data:
            return PasswordStatusResponse.model_validate(data)
        return data
