import secrets
import string
import logging
import httpx

from .config import GitServerSettings, get_git_server_settings
from .exceptions import (
    GitServerAuthError,
    GitServerConnectionError,
    GitServerError,
    GitUserAlreadyExistsError,
    GitUserNotFoundError,
)
from .schemas import CreateGitUserRequest, GitServerHealthResponse, GitUser, UpdateGitUserRequest

logger = logging.getLogger(__name__)

_BASE = "/api/v1"


def _generate_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(24))


def _map_user(data: dict) -> GitUser:
    return GitUser(
        id=data["id"],
        username=data["login"],
        email=data["email"],
        display_name=data.get("full_name") or data["login"],
        is_active=not data.get("prohibit_login", False),
    )


class ForgejoClient:
    def __init__(self, settings: GitServerSettings | None = None):
        self._settings = settings or get_git_server_settings()
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.forgejo_url,
                auth=(self._settings.forgejo_admin_username, self._settings.forgejo_admin_password),
                timeout=15.0,
            )
        return self._client

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        client = self._get_client()
        try:
            resp = await client.request(method, f"{_BASE}{path}", **kwargs)
        except httpx.ConnectError as e:
            raise GitServerConnectionError(f"Cannot reach Forgejo at {self._settings.forgejo_url}") from e
        except httpx.TimeoutException as e:
            raise GitServerConnectionError("Forgejo request timed out") from e

        if resp.status_code == 401:
            raise GitServerAuthError("Invalid or missing Forgejo admin token")
        return resp

    async def health(self) -> GitServerHealthResponse:
        resp = await self._request("GET", "/version")
        if resp.status_code != 200:
            return GitServerHealthResponse(status="error", server_type="forgejo")
        version = resp.json().get("version")
        return GitServerHealthResponse(status="ok", server_type="forgejo", version=version)

    async def create_user(self, req: CreateGitUserRequest) -> GitUser:
        payload = {
            "source_id": 0,
            "login_name": req.username,
            "username": req.username,
            "email": req.email,
            "full_name": req.display_name,
            "password": req.password or _generate_password(),
            "must_change_password": False,
            "send_notify": False,
            "visibility": "private",
        }
        resp = await self._request("POST", "/admin/users", json=payload)
        if resp.status_code == 422:
            raise GitUserAlreadyExistsError(req.username)
        if not resp.is_success:
            raise GitServerError(f"Create user failed: {resp.status_code} {resp.text}")
        return _map_user(resp.json())

    async def get_user(self, username: str) -> GitUser:
        resp = await self._request("GET", f"/users/{username}")
        if resp.status_code == 404:
            raise GitUserNotFoundError(username)
        if not resp.is_success:
            raise GitServerError(f"Get user failed: {resp.status_code} {resp.text}")
        return _map_user(resp.json())

    async def update_user(self, username: str, req: UpdateGitUserRequest) -> GitUser:
        payload: dict = {"source_id": 0, "login_name": username}
        if req.email is not None:
            payload["email"] = req.email
        if req.display_name is not None:
            payload["full_name"] = req.display_name
        resp = await self._request("PATCH", f"/admin/users/{username}", json=payload)
        if resp.status_code == 404:
            raise GitUserNotFoundError(username)
        if not resp.is_success:
            raise GitServerError(f"Update user failed: {resp.status_code} {resp.text}")
        return _map_user(resp.json())

    async def delete_user(self, username: str) -> None:
        resp = await self._request("DELETE", f"/admin/users/{username}")
        if resp.status_code == 404:
            raise GitUserNotFoundError(username)
        if not resp.is_success:
            raise GitServerError(f"Delete user failed: {resp.status_code} {resp.text}")

    async def suspend_user(self, username: str) -> None:
        resp = await self._request(
            "PATCH",
            f"/admin/users/{username}",
            json={"source_id": 0, "login_name": username, "login_disabled": True},
        )
        if resp.status_code == 404:
            raise GitUserNotFoundError(username)
        if not resp.is_success:
            raise GitServerError(f"Suspend user failed: {resp.status_code} {resp.text}")

    async def activate_user(self, username: str) -> None:
        resp = await self._request(
            "PATCH",
            f"/admin/users/{username}",
            json={"source_id": 0, "login_name": username, "login_disabled": False},
        )
        if resp.status_code == 404:
            raise GitUserNotFoundError(username)
        if not resp.is_success:
            raise GitServerError(f"Activate user failed: {resp.status_code} {resp.text}")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


_client: ForgejoClient | None = None


def get_forgejo_client() -> ForgejoClient:
    global _client
    if _client is None:
        _client = ForgejoClient()
    return _client
