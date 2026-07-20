"""
Async HTTP client for Coder API.
"""

import asyncio
import logging
import secrets
import string
from typing import Any, Optional

import httpx

from .config import CoderSettings, get_coder_settings
from .exceptions import (
    CoderAPIError,
    CoderAuthenticationError,
    CoderConnectionError,
    CoderTemplateNotFoundError,
    CoderTimeoutError,
    CoderUserExistsError,
    CoderUserNotFoundError,
    CoderWorkspaceActionError,
    CoderWorkspaceExistsError,
    CoderWorkspaceNotFoundError,
)
from .naming import derive_workspace_name, sanitize_workspace_name
from .schemas import (
    CoderTemplate,
    CoderUser,
    CoderUserCreate,
    CoderWorkspace,
    CoderWorkspaceCreate,
    ProvisionResult,
    WorkspaceDetails,
    WorkspaceStatus,
)

logger = logging.getLogger(__name__)


def _generate_coder_password(length: int = 24) -> str:
    """Generate a random password that satisfies Coder's requirements.

    Coder requires: min 6 chars. We generate a strong random password
    with uppercase, lowercase, digits, and special chars since this
    password is never seen or used by the user (auth is via ForwardAuth).
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    # Ensure at least one of each category
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%&*"),
    ]
    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    # Shuffle to avoid predictable positions
    result = list(password)
    secrets.SystemRandom().shuffle(result)
    return "".join(result)


class CoderClient:
    """
    Async client for Coder API.

    Handles authentication, user management, and workspace operations.
    """

    def __init__(self, settings: Optional[CoderSettings] = None):
        """
        Initialize Coder client.

        Args:
            settings: Optional CoderSettings. If not provided, loads from environment.
        """
        self.settings = settings or get_coder_settings()
        self._session_token: Optional[str] = None
        self._org_id: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "CoderClient":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure HTTP client is initialized."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.settings.url,
                timeout=httpx.Timeout(self.settings.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        self._session_token = None
        self._org_id = None

    async def _get_session_token(self) -> str:
        """
        Authenticate as admin and get session token.

        Returns:
            Session token string

        Raises:
            CoderAuthenticationError: If authentication fails
            CoderConnectionError: If connection to Coder fails
        """
        if self._session_token:
            return self._session_token

        client = await self._ensure_client()

        try:
            # Drop any session cookie captured from a previous login response:
            # a stale cookie shadows the header token on later requests AND
            # trips Coder's CSRF check on this login POST itself.
            client.cookies.clear()
            resp = await client.post(
                "/api/v2/users/login",
                json={
                    "email": self.settings.admin_email,
                    "password": self.settings.admin_password,
                },
            )

            if resp.status_code != 201:
                raise CoderAuthenticationError(
                    detail=resp.text,
                    response_data=self._safe_json(resp),
                )

            data = resp.json()
            self._session_token = data["session_token"]
            logger.debug("Successfully authenticated with Coder API")
            return self._session_token

        except httpx.ConnectError as e:
            raise CoderConnectionError(detail=str(e))
        except httpx.TimeoutException as e:
            raise CoderTimeoutError("authentication", self.settings.timeout)

    async def _get_org_id(self) -> str:
        """
        Get the default organization ID.

        Returns:
            Organization ID string

        Raises:
            CoderAPIError: If no organizations found
        """
        if self._org_id:
            return self._org_id

        resp = await self._request("GET", "/api/v2/organizations", ok=(200,))

        orgs = resp.json()
        if not orgs:
            raise CoderAPIError("No organizations found in Coder")

        self._org_id = orgs[0]["id"]
        return self._org_id

    def _get_headers(self, token: str) -> dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "Coder-Session-Token": token,
        }
        # Add admin secret if configured (for Traefik-protected endpoints)
        if self.settings.admin_api_secret:
            headers["X-Admin-Secret"] = self.settings.admin_api_secret
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Optional[dict] = None,
        ok: Optional[tuple[int, ...]] = (200,),
        admin_headers: bool = False,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        """Issue an authenticated request against the Coder API.

        Collapses the ``token = await self._get_session_token(); client =
        await self._ensure_client()`` boilerplate plus header building that
        every endpoint used to repeat. On a 401 the cached session token is
        dropped and the request is replayed once with a fresh admin login
        (session tokens expire server-side).

        Args:
            method: HTTP method (GET/POST/PUT/PATCH/DELETE).
            path: API path relative to the configured base URL.
            json: Optional JSON request body.
            params: Optional query parameters.
            ok: Status codes treated as success. If the response status is not
                in ``ok`` a ``CoderAPIError`` is raised. Pass a wider tuple to
                let the caller special-case a status (e.g. ``409``/``404``);
                pass ``None`` to skip the check entirely when the caller handles
                every status itself (e.g. best-effort ``bool``-returning ops).
            admin_headers: When ``True`` the request carries the full admin
                header set from :meth:`_get_headers` (adds ``X-Admin-Secret``
                when configured). When ``False`` only ``Coder-Session-Token`` is
                sent. This preserves the exact per-endpoint header set each call
                site used before this refactor.
            timeout: Optional per-request timeout override (else the client's
                configured default is used).

        Returns:
            The (already status-checked, unless ``ok is None``) response.

        Raises:
            CoderAPIError: If ``ok`` is not ``None`` and the response status is
                not contained in it.
        """
        token = await self._get_session_token()
        client = await self._ensure_client()

        headers = self._get_headers(token) if admin_headers else {"Coder-Session-Token": token}

        kwargs: dict[str, Any] = {"headers": headers}
        if json is not None:
            kwargs["json"] = json
        if params is not None:
            kwargs["params"] = params
        if timeout is not None:
            kwargs["timeout"] = timeout

        resp = await client.request(method, path, **kwargs)

        if resp.status_code == 401:
            # Coder session tokens expire (idle sessions are not refreshed), but
            # this client is a process-lifetime singleton that caches its token —
            # without re-auth every call would keep failing until a restart.
            logger.info("Coder session token rejected (401), re-authenticating")
            self._session_token = None
            token = await self._get_session_token()
            kwargs["headers"] = (
                self._get_headers(token) if admin_headers else {"Coder-Session-Token": token}
            )
            resp = await client.request(method, path, **kwargs)

        if ok is not None and resp.status_code not in ok:
            raise CoderAPIError(
                f"Coder API request failed: {method} {path} (status {resp.status_code})",
                status_code=resp.status_code,
                detail=resp.text,
            )

        return resp

    @staticmethod
    def _safe_json(resp: httpx.Response) -> Optional[dict]:
        """Safely parse JSON response."""
        try:
            return resp.json()
        except Exception:
            return None

    @staticmethod
    def _sanitize_username(username: str) -> str:
        """
        Sanitize username for Coder requirements.

        Coder usernames must:
        - Be lowercase
        - Start with a letter (a-z)
        - Only contain alphanumeric characters and hyphens
        - Be max 32 characters

        For UUIDs passed from the backend, we ALWAYS add a 'u' prefix
        to create the u{uuid} format expected by ForwardAuth.

        Args:
            username: Raw username (e.g., UUID from backend user.id)

        Returns:
            Sanitized username in u{uuid} format valid for Coder
        """
        import re

        # Lowercase and remove invalid characters (keep only alphanumeric and hyphens)
        clean = re.sub(r"[^a-z0-9-]", "", username.lower())

        # ALWAYS prepend 'u' - unconditionally (required by ForwardAuth)
        clean = "u" + clean

        # Truncate to 32 characters (Coder's limit)
        clean = clean[:32]

        # Remove trailing hyphens
        clean = clean.rstrip("-")

        return clean

    # -------------------------------------------------------------------------
    # User operations
    # -------------------------------------------------------------------------

    async def get_user(self, username_or_email: str) -> CoderUser:
        """
        Get user by username or email.

        Args:
            username_or_email: Username or email to look up

        Returns:
            CoderUser instance

        Raises:
            CoderUserNotFoundError: If user not found
        """
        # Try by username first. ``ok=None`` preserves the original behavior of
        # treating every non-200 (not just 404) as "not found".
        resp = await self._request(
            "GET", f"/api/v2/users/{username_or_email}", ok=None
        )

        if resp.status_code == 200:
            return CoderUser.from_api(resp.json())

        # If not found and looks like email, search by email
        if resp.status_code == 404 and "@" in username_or_email:
            return await self._find_user_by_email(username_or_email)

        raise CoderUserNotFoundError(username_or_email)

    async def _find_user_by_email(self, email: str) -> CoderUser:
        """Find user by email address."""
        # List users and filter by email
        resp = await self._request(
            "GET", "/api/v2/users", params={"q": email}, ok=(200,)
        )

        data = resp.json()
        users = data.get("users", [])

        for user in users:
            if user.get("email", "").lower() == email.lower():
                return CoderUser.from_api(user)

        raise CoderUserNotFoundError(email)

    async def user_exists(self, email: str) -> bool:
        """
        Check if a user exists by email.

        Args:
            email: Email address to check

        Returns:
            True if user exists, False otherwise
        """
        try:
            await self._find_user_by_email(email)
            return True
        except CoderUserNotFoundError:
            return False

    async def create_user(self, user_data: CoderUserCreate) -> CoderUser:
        """
        Create a new Coder user.

        Args:
            user_data: User creation data

        Returns:
            Created CoderUser instance

        Raises:
            CoderUserExistsError: If user already exists
            CoderAPIError: If creation fails
        """
        org_id = await self._get_org_id()

        payload: dict[str, Any] = {
            "username": user_data.username,
            "email": user_data.email,
            "password": user_data.password,
            "user_status": "active",
            "organization_ids": [org_id],
        }

        if user_data.full_name:
            payload["name"] = user_data.full_name

        resp = await self._request(
            "POST",
            "/api/v2/users",
            json=payload,
            admin_headers=True,
            ok=(200, 201, 409),
        )

        if resp.status_code == 409:
            raise CoderUserExistsError(user_data.email)

        data = resp.json()
        logger.info(f"Created Coder user: {user_data.username}")

        return CoderUser.from_api(data)

    async def update_user_password(self, username: str, new_password: str) -> bool:
        """
        Update a user's password.

        Args:
            username: Username of the user
            new_password: New password to set

        Returns:
            True if password was updated successfully
        """
        # Try the standard password update endpoint
        resp = await self._request(
            "PUT",
            f"/api/v2/users/{username}/password",
            json={"password": new_password, "old_password": ""},
            admin_headers=True,
            ok=None,
        )

        if resp.status_code in (200, 204):
            logger.info(f"Updated password for Coder user: {username}")
            return True

        logger.warning(f"Password update failed for {username}: status={resp.status_code}, response={resp.text}")
        return False

    async def login_user(self, email: str, password: str) -> Optional[str]:
        """
        Login a user to Coder and get their session token.

        Args:
            email: User's email
            password: User's password

        Returns:
            Session token if successful, None otherwise
        """
        client = await self._ensure_client()

        resp = await client.post(
            "/api/v2/users/login",
            json={"email": email, "password": password},
        )

        if resp.status_code == 201:
            data = resp.json()
            session_token = data.get("session_token")
            logger.info(f"User logged in successfully: {email}")
            return session_token

        logger.warning(f"Login failed for {email}: status={resp.status_code}, response={resp.text}")
        return None

    async def create_user_api_key(self, username: str, key_name: str = "computor-access") -> Optional[str]:
        """
        Create an API key for a user (admin function).

        Args:
            username: Username to create key for
            key_name: Name for the API key

        Returns:
            API key if successful, None otherwise
        """
        resp = await self._request(
            "POST",
            f"/api/v2/users/{username}/keys",
            json={"lifetime_seconds": 86400 * 7},  # 7 days
            admin_headers=True,
            ok=None,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            api_key = data.get("key")
            logger.info(f"Created API key for user: {username}")
            return api_key

        logger.warning(f"Failed to create API key for {username}: status={resp.status_code}, response={resp.text}")
        return None

    async def get_or_create_user(self, user_data: CoderUserCreate) -> tuple[CoderUser, bool]:
        """
        Get existing user or create new one.

        Password is auto-generated and only used for Coder API user creation.
        Actual authentication is handled by computor-backend via ForwardAuth.

        Args:
            user_data: User data for creation if needed

        Returns:
            Tuple of (CoderUser, created: bool)
        """
        try:
            user = await self._find_user_by_email(user_data.email)
            return user, False
        except CoderUserNotFoundError:
            user = await self.create_user(user_data)
            return user, True

    async def delete_user(self, username: str) -> bool:
        """
        Delete a Coder user and all their workspaces.

        Args:
            username: Username to delete

        Returns:
            True if deleted successfully
        """
        resp = await self._request(
            "DELETE",
            f"/api/v2/users/{username}",
            admin_headers=True,
            ok=None,
        )

        if resp.status_code in (200, 204):
            logger.info(f"Deleted Coder user: {username}")
            return True

        return False

    # -------------------------------------------------------------------------
    # Template operations
    # -------------------------------------------------------------------------

    async def list_templates(self) -> list[CoderTemplate]:
        """
        List all available templates.

        Returns:
            List of CoderTemplate instances
        """
        resp = await self._request("GET", "/api/v2/templates", ok=(200,))

        templates = resp.json()
        return [
            CoderTemplate(
                id=t["id"],
                name=t["name"],
                display_name=t.get("display_name"),
                description=t.get("description"),
                icon=t.get("icon"),
                active_version_id=t.get("active_version_id"),
                created_at=t.get("created_at"),
            )
            for t in templates
        ]

    async def get_template_id(self, template_name: str) -> str:
        """
        Get template ID by name.

        Args:
            template_name: Template name (e.g., "python3.13-workspace")

        Returns:
            Template ID string

        Raises:
            CoderTemplateNotFoundError: If template not found
        """
        templates = await self.list_templates()

        for tpl in templates:
            if tpl.name == template_name:
                return tpl.id

        raise CoderTemplateNotFoundError(template_name)

    async def get_template_active_version(self, template_name: str) -> str:
        """Return the active (latest published) template version id by name.

        This is the version a fleet rollout moves workspaces onto.

        Raises:
            CoderTemplateNotFoundError: If template not found
            CoderAPIError: If the template has no active version
        """
        for tpl in await self.list_templates():
            if tpl.name == template_name:
                if not tpl.active_version_id:
                    raise CoderAPIError(f"Template '{template_name}' has no active version")
                return tpl.active_version_id
        raise CoderTemplateNotFoundError(template_name)

    async def get_template(self, name: str) -> dict:
        """Get a template's raw record by name from the default organization.

        Uses the org-scoped ``GET /organizations/default/templates/{name}``
        endpoint (unlike :meth:`list_templates`, which returns typed summaries),
        and returns the parsed JSON so callers can read fields such as ``id``.

        Raises:
            CoderAPIError: If the template cannot be fetched.
        """
        resp = await self._request(
            "GET",
            f"/api/v2/organizations/default/templates/{name}",
            ok=(200,),
        )
        return resp.json()

    async def patch_template_meta(
        self,
        template_id: str,
        *,
        ttl_ms: int,
        activity_bump_ms: int,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> dict:
        """Patch a template's TTL settings and display metadata, returning the
        updated record.

        Metadata fields are only included in the PATCH when not None; pass an
        empty string to explicitly clear a field.

        Raises:
            CoderAPIError: If the patch is rejected.
        """
        payload: dict[str, Any] = {
            "default_ttl_ms": ttl_ms,
            "activity_bump_ms": activity_bump_ms,
        }
        if display_name is not None:
            payload["display_name"] = display_name
        if description is not None:
            payload["description"] = description
        if icon is not None:
            payload["icon"] = icon
        resp = await self._request(
            "PATCH",
            f"/api/v2/templates/{template_id}",
            json=payload,
            ok=(200,),
        )
        return resp.json()

    # -------------------------------------------------------------------------
    # Workspace operations
    # -------------------------------------------------------------------------

    async def extend_workspace_deadline(
        self,
        workspace_id: str,
        *,
        extend_ms: int,
    ) -> bool:
        """Push a running workspace's auto-stop deadline to ``now + extend_ms``.

        Uses Coder's ``PUT /workspaces/{id}/extend``, which sets an absolute
        deadline. This is best-effort keepalive (see ``coder/keepalive.py``):
        it returns ``False`` — never raises — when the workspace is stopped,
        has no deadline, or Coder otherwise rejects the request, so callers on
        the request hot path are never disturbed.

        Args:
            workspace_id: Coder workspace UUID.
            extend_ms: Milliseconds from now for the new deadline.

        Returns:
            True if Coder accepted the new deadline.
        """
        from datetime import datetime, timedelta, timezone

        # isoformat() on a timezone-aware datetime yields the RFC3339 timestamp
        # Coder's extend endpoint expects.
        deadline = datetime.now(timezone.utc) + timedelta(milliseconds=extend_ms)
        resp = await self._request(
            "PUT",
            f"/api/v2/workspaces/{workspace_id}/extend",
            json={"deadline": deadline.isoformat()},
            ok=None,
        )
        return resp.status_code == 200

    @staticmethod
    def _parse_workspace_summary(ws: dict) -> CoderWorkspace:
        """Build a CoderWorkspace from a Coder /workspaces list entry."""
        latest = ws.get("latest_build") or {}
        return CoderWorkspace(
            id=ws["id"],
            name=ws["name"],
            owner_id=ws["owner_id"],
            owner_name=ws.get("owner_name"),
            template_id=ws["template_id"],
            template_name=ws.get("template_name"),
            template_display_name=ws.get("template_display_name"),
            template_version_id=latest.get("template_version_id"),
            template_version_name=latest.get("template_version_name"),
            latest_build_transition=latest.get("transition"),
            latest_build_status=latest.get("status"),
            latest_build_id=latest.get("id"),
            automatic_updates=ws.get("automatic_updates"),
            created_at=ws.get("created_at"),
            updated_at=ws.get("updated_at"),
        )

    async def list_all_workspaces(self, limit: int = 1000) -> list[CoderWorkspace]:
        """List every workspace on the server (admin-only fleet view).

        Uses the same /workspaces endpoint as ``get_user_workspaces`` but with
        no owner filter, so an admin session sees all users' workspaces.
        """
        resp = await self._request(
            "GET", "/api/v2/workspaces", params={"limit": limit}, ok=(200,)
        )

        return [self._parse_workspace_summary(ws) for ws in resp.json().get("workspaces", [])]

    async def get_workspace(
        self,
        username: str,
        workspace_name: str,
    ) -> WorkspaceDetails:
        """
        Get workspace details for a user.

        Args:
            username: User's username
            workspace_name: Workspace name

        Returns:
            WorkspaceDetails instance

        Raises:
            CoderWorkspaceNotFoundError: If workspace not found
        """
        # ``ok=None`` preserves the original behavior of mapping every non-200
        # to CoderWorkspaceNotFoundError.
        resp = await self._request(
            "GET",
            f"/api/v2/users/{username}/workspace/{workspace_name}",
            ok=None,
        )

        if resp.status_code != 200:
            raise CoderWorkspaceNotFoundError(f"{username}/{workspace_name}")

        return self._parse_workspace_details(resp.json())

    async def get_user_workspaces(self, username: str) -> list[CoderWorkspace]:
        """
        List all workspaces for a user.

        Args:
            username: User's username

        Returns:
            List of CoderWorkspace instances
        """
        resp = await self._request(
            "GET",
            "/api/v2/workspaces",
            params={"q": f"owner:{username}"},
            ok=(200,),
        )

        data = resp.json()
        return [self._parse_workspace_summary(ws) for ws in data.get("workspaces", [])]

    async def workspace_exists(
        self,
        username: str,
        workspace_name: str,
    ) -> bool:
        """
        Check if a workspace exists for a user.

        Args:
            username: User's username
            workspace_name: Workspace name

        Returns:
            True if workspace exists
        """
        try:
            await self.get_workspace(username, workspace_name)
            return True
        except CoderWorkspaceNotFoundError:
            return False

    async def create_workspace(
        self,
        username: str,
        workspace_data: CoderWorkspaceCreate,
    ) -> CoderWorkspace:
        """
        Create a workspace for a user.

        Args:
            username: User's username
            workspace_data: Workspace creation data

        Returns:
            Created CoderWorkspace instance

        Raises:
            CoderWorkspaceExistsError: If workspace already exists
            CoderAPIError: If creation fails
        """
        template_id = await self.get_template_id(workspace_data.template)

        workspace_name = workspace_data.name

        payload: dict[str, Any] = {
            "name": workspace_name,
            "template_id": template_id,
        }

        # Add rich parameter values (per-workspace Terraform variables)
        rich_params = []
        if workspace_data.code_server_password:
            rich_params.append({
                "name": "code_server_password",
                "value": workspace_data.code_server_password,
            })
        if workspace_data.computor_auth_token:
            rich_params.append({
                "name": "computor_auth_token",
                "value": workspace_data.computor_auth_token,
            })
            logger.info(f"Adding computor_auth_token to workspace (prefix: {workspace_data.computor_auth_token[:15]}...)")
        else:
            logger.warning("No computor_auth_token provided for workspace creation!")
        if workspace_data.home_mode:
            rich_params.append({
                "name": "home_mode",
                "value": workspace_data.home_mode,
            })
        if rich_params:
            payload["rich_parameter_values"] = rich_params
            logger.info(f"Sending rich_parameter_values: {[p['name'] for p in rich_params]}")

        resp = await self._request(
            "POST",
            f"/api/v2/organizations/default/members/{username}/workspaces",
            json=payload,
            admin_headers=True,
            ok=(200, 201, 409),
            timeout=self.settings.workspace_timeout,
        )

        if resp.status_code == 409:
            raise CoderWorkspaceExistsError(workspace_name)

        data = resp.json()
        logger.info(f"Created workspace: {workspace_name} for user {username}")

        return CoderWorkspace(
            id=data["id"],
            name=data["name"],
            owner_id=data["owner_id"],
            owner_name=data.get("owner_name"),
            template_id=data["template_id"],
            template_name=data.get("template_name"),
            template_display_name=data.get("template_display_name"),
            latest_build_status=data.get("latest_build", {}).get("status"),
            latest_build_id=data.get("latest_build", {}).get("id"),
            created_at=data.get("created_at"),
        )

    async def delete_workspace(
        self,
        username: str,
        workspace_name: str,
    ) -> bool:
        """
        Delete a workspace.

        Args:
            username: User's username
            workspace_name: Workspace name

        Returns:
            True if deleted successfully
        """
        logger.info(f"delete_workspace called: username={username}, workspace_name={workspace_name}")

        # First get workspace ID
        try:
            details = await self.get_workspace(username, workspace_name)
            logger.info(f"Found workspace to delete: id={details.workspace.id}, name={details.workspace.name}")
        except CoderWorkspaceNotFoundError:
            logger.info(f"Workspace {workspace_name} not found - already deleted")
            return True  # Already doesn't exist
        except Exception as e:
            logger.error(f"Error getting workspace for delete: {e}")
            return False

        # Coder deletes workspaces by creating a build with transition="delete"
        resp = await self._request(
            "POST",
            f"/api/v2/workspaces/{details.workspace.id}/builds",
            json={"transition": "delete"},
            admin_headers=True,
            ok=None,
        )

        if resp.status_code in (200, 201, 202):
            logger.info(f"Delete build started for workspace: {workspace_name} (status={resp.status_code})")
            return True

        logger.error(f"Failed to delete workspace {workspace_name}: status={resp.status_code}, response={resp.text}")
        return False

    async def start_workspace(
        self,
        username: str,
        workspace_name: str,
    ) -> bool:
        """
        Start a stopped workspace.

        Args:
            username: User's username
            workspace_name: Workspace name

        Returns:
            True if start initiated successfully
        """
        details = await self.get_workspace(username, workspace_name)
        return await self._workspace_transition(
            details.workspace.id,
            "start",
        )

    async def stop_workspace(
        self,
        username: str,
        workspace_name: str,
    ) -> bool:
        """
        Stop a running workspace.

        Args:
            username: User's username
            workspace_name: Workspace name

        Returns:
            True if stop initiated successfully
        """
        details = await self.get_workspace(username, workspace_name)
        return await self._workspace_transition(
            details.workspace.id,
            "stop",
        )

    async def _workspace_transition(
        self,
        workspace_id: str,
        transition: str,
    ) -> bool:
        """Execute workspace state transition (start/stop)."""
        # Get workspace to find template version
        resp = await self._request(
            "GET", f"/api/v2/workspaces/{workspace_id}", ok=None
        )

        if resp.status_code != 200:
            return False

        workspace = resp.json()
        template_version_id = workspace["latest_build"]["template_version_id"]

        # Create transition build
        resp = await self._request(
            "POST",
            f"/api/v2/workspaces/{workspace_id}/builds",
            json={
                "template_version_id": template_version_id,
                "transition": transition,
            },
            ok=None,
            timeout=self.settings.workspace_timeout,
        )

        success = resp.status_code in (200, 201)
        if success:
            logger.info(f"Workspace {workspace_id}: {transition} initiated")
        return success

    def _parse_workspace_details(self, data: dict) -> WorkspaceDetails:
        """Parse workspace details from API response."""
        workspace = CoderWorkspace(
            id=data["id"],
            name=data["name"],
            owner_id=data["owner_id"],
            owner_name=data.get("owner_name"),
            template_id=data["template_id"],
            template_name=data.get("template_name"),
            template_display_name=data.get("template_display_name"),
            latest_build_status=data.get("latest_build", {}).get("status"),
            latest_build_id=data.get("latest_build", {}).get("id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

        # Determine status from latest build
        latest_build = data.get("latest_build", {})
        job = latest_build.get("job", {})
        status = self._determine_workspace_status(latest_build, job)

        # Extract access URLs from resources
        access_url = None
        code_server_url = None
        resources = {}
        agent_status = None
        agent_lifecycle = None

        # Build access URL for running workspaces via Traefik
        if status == WorkspaceStatus.RUNNING and self.settings.workspace_base_url:
            owner_name = data.get("owner_name", "")
            workspace_name = data["name"]
            base_url = self.settings.workspace_base_url.rstrip("/")
            access_url = f"{base_url}/{owner_name}/{workspace_name}/"

        # Extract code-server URL from agent apps
        # Logged at debug: the workspace-launch page polls this endpoint every 2s.
        logger.debug(f"Parsing workspace resources: {len(latest_build.get('resources', []))} resources")
        for resource in latest_build.get("resources", []):
            resource_name = resource.get("name", "unknown")
            agents = resource.get("agents", [])
            logger.debug(f"Resource '{resource_name}' has {len(agents)} agents")

            for agent in agents:
                agent_name = agent.get("name", "unknown")
                agent_status = agent.get("status")
                # `status` is the agent's *connection* state (connecting/connected/...);
                # `lifecycle_state` is how far its startup script got, which is what
                # tells us the service inside is actually up.
                agent_lifecycle = agent.get("lifecycle_state")
                apps = agent.get("apps", [])
                logger.debug(
                    f"Agent '{agent_name}' status={agent_status} "
                    f"lifecycle={agent_lifecycle}, apps count={len(apps)}"
                )

                # Store agent info in resources
                resources[agent_name] = {
                    "status": agent_status,
                    "lifecycle_state": agent_lifecycle,
                    "apps": [app.get("slug") for app in apps],
                }

                # Look for code-server app (check multiple possible slugs)
                for app in apps:
                    app_slug = app.get("slug", "").lower()
                    app_url = app.get("url")
                    logger.debug(f"App: slug='{app_slug}', url={app_url}")

                    if any(term in app_slug for term in ["code", "vscode", "vs-code"]):
                        # Skip localhost URLs - they're internal container URLs not accessible from outside
                        if app_url and "localhost" not in app_url and "127.0.0.1" not in app_url:
                            code_server_url = app_url
                            logger.debug(f"Found code-server URL: {code_server_url}")
                        else:
                            logger.debug(f"Skipping internal URL: {app_url}")
                        break

        # Generate code-server URL for running workspaces via Traefik
        if status == WorkspaceStatus.RUNNING and not code_server_url and self.settings.workspace_base_url:
            owner_name = data.get("owner_name", "")
            workspace_name = data["name"]
            base_url = self.settings.workspace_base_url.rstrip("/")
            code_server_url = f"{base_url}/{owner_name}/{workspace_name}/"
            logger.debug(f"Using Traefik code-server URL: {code_server_url}")

        logger.debug(f"Workspace details: status={status}, access_url={access_url}, code_server_url={code_server_url}")

        return WorkspaceDetails(
            workspace=workspace,
            status=status,
            access_url=access_url,
            code_server_url=code_server_url,
            health=data.get("health", {}).get("healthy"),
            resources=resources,
            agent_lifecycle=agent_lifecycle,
            ready=status == WorkspaceStatus.RUNNING and agent_lifecycle == "ready",
        )

    @staticmethod
    def _determine_workspace_status(
        latest_build: dict,
        job: dict,
    ) -> WorkspaceStatus:
        """Determine workspace status from build and job info."""
        job_status = job.get("status", "")
        transition = latest_build.get("transition", "")

        if job_status == "running":
            if transition == "start":
                return WorkspaceStatus.STARTING
            elif transition == "stop":
                return WorkspaceStatus.STOPPING
            elif transition == "delete":
                return WorkspaceStatus.DELETING
            return WorkspaceStatus.PENDING

        if job_status == "succeeded":
            if transition == "start":
                return WorkspaceStatus.RUNNING
            elif transition == "stop":
                return WorkspaceStatus.STOPPED
            elif transition == "delete":
                return WorkspaceStatus.DELETED

        if job_status == "failed":
            return WorkspaceStatus.FAILED

        if job_status == "canceled":
            return WorkspaceStatus.CANCELED

        return WorkspaceStatus.PENDING

    async def _update_workspace_token(
        self,
        workspace_id: str,
        computor_auth_token: str,
    ) -> bool:
        """
        Update an existing workspace with a new auth token.

        This triggers a rebuild of the workspace with the new token value.

        Args:
            workspace_id: Workspace ID to update
            computor_auth_token: New token value

        Returns:
            True if update was initiated successfully
        """
        # Get workspace to find template version (no admin secret, as before)
        resp = await self._request(
            "GET", f"/api/v2/workspaces/{workspace_id}", ok=None
        )

        if resp.status_code != 200:
            logger.error(f"Failed to get workspace for token update: {resp.status_code}")
            return False

        workspace = resp.json()
        latest_build = workspace.get("latest_build") or {}
        template_version_id = latest_build.get("template_version_id")
        if not template_version_id:
            logger.error(
                f"Workspace {workspace_id}: latest build has no "
                f"template_version_id; cannot update token"
            )
            return False

        # Create a new build with the updated token parameter. home_mode is
        # immutable per workspace; re-send its current value so the rebuild
        # cannot reset a scratch-home workspace to the shared-home default.
        rich_params = [{
            "name": "computor_auth_token",
            "value": computor_auth_token,
        }]
        build_id = latest_build.get("id")
        if build_id:
            home_mode = await self._get_build_param(build_id, "home_mode")
            if home_mode is not None:
                rich_params.append({"name": "home_mode", "value": home_mode})

        resp = await self._request(
            "POST",
            f"/api/v2/workspaces/{workspace_id}/builds",
            json={
                "template_version_id": template_version_id,
                "transition": "start",
                "rich_parameter_values": rich_params,
            },
            admin_headers=True,
            ok=None,
            timeout=self.settings.workspace_timeout,
        )

        success = resp.status_code in (200, 201)
        if success:
            logger.info(f"Workspace {workspace_id}: token update build initiated")
        else:
            logger.error(f"Failed to update workspace token: {resp.status_code} - {resp.text}")
        return success

    async def _get_build_param(
        self, build_id: str, name: str
    ) -> Optional[str]:
        """Read one rich-parameter value from a workspace build so it can be
        preserved across a new build (omitted params reset to their default)."""
        resp = await self._request(
            "GET",
            f"/api/v2/workspacebuilds/{build_id}/parameters",
            admin_headers=True,
            ok=None,
        )
        if resp.status_code != 200:
            return None
        for p in resp.json():
            if p.get("name") == name:
                return p.get("value")
        return None

    async def set_workspace_auto_update(
        self, workspace_id: str, always: bool = True
    ) -> bool:
        """Set a workspace's automatic-updates policy so it adopts the template's
        active version on its next start. Best-effort."""
        resp = await self._request(
            "PUT",
            f"/api/v2/workspaces/{workspace_id}/autoupdates",
            json={"automatic_updates": "always" if always else "never"},
            admin_headers=True,
            ok=None,
        )
        return resp.status_code in (200, 204)

    async def update_workspace_to_version(
        self,
        workspace_id: str,
        template_version_id: str,
    ) -> bool:
        """Rebuild a workspace onto a specific template version (fleet update),
        preserving its computor_auth_token so the extension stays authenticated.

        Issues a ``start`` build on the new version — for workspaces to update
        immediately. For stopped workspaces prefer ``set_workspace_auto_update``
        so they adopt the new version on next start rather than being
        force-started.
        """
        resp = await self._request(
            "GET",
            f"/api/v2/workspaces/{workspace_id}",
            admin_headers=True,
            ok=None,
        )
        if resp.status_code != 200:
            logger.error(
                f"Failed to load workspace {workspace_id} for version update: {resp.status_code}"
            )
            return False
        latest = (resp.json() or {}).get("latest_build") or {}

        # Preserve the current auth token; omitting it resets the param to its
        # "" default and de-authenticates the extension. Same for home_mode:
        # a scratch-home workspace must not silently rebuild onto the shared home.
        rich_params: list[dict] = []
        build_id = latest.get("id")
        if build_id:
            current_token = await self._get_build_param(build_id, "computor_auth_token")
            if current_token is not None:
                rich_params.append({"name": "computor_auth_token", "value": current_token})
            home_mode = await self._get_build_param(build_id, "home_mode")
            if home_mode is not None:
                rich_params.append({"name": "home_mode", "value": home_mode})

        resp = await self._request(
            "POST",
            f"/api/v2/workspaces/{workspace_id}/builds",
            json={
                "template_version_id": template_version_id,
                "transition": "start",
                "rich_parameter_values": rich_params,
            },
            admin_headers=True,
            ok=None,
            timeout=self.settings.workspace_timeout,
        )
        success = resp.status_code in (200, 201)
        if success:
            logger.info(
                f"Workspace {workspace_id}: update to version {template_version_id} initiated"
            )
        else:
            logger.error(
                f"Failed to update workspace {workspace_id} to version: {resp.status_code} - {resp.text}"
            )
        return success

    # -------------------------------------------------------------------------
    # Provisioning (combined user + workspace)
    # -------------------------------------------------------------------------

    async def provision_workspace(
        self,
        user_email: str,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        template: Optional[str] = None,
        workspace_name: Optional[str] = None,
        computor_auth_token: Optional[str] = None,
        home_mode: Optional[str] = None,
    ) -> ProvisionResult:
        """
        Full provisioning: get or create user and workspace.

        This is the main method for on-demand workspace provisioning.
        Uses email to check if user already exists in Coder.
        A random password is generated for the Coder user account since
        authentication is handled by the computor-backend via ForwardAuth.

        Args:
            user_email: User's email (must match backend user)
            username: Username (derived from email if not provided)
            full_name: User's display name
            template: Workspace template name (defaults to settings.default_template)
            workspace_name: Custom workspace name (defaults to a name derived
                from the template, e.g. 'python-workspace' -> 'python')
            computor_auth_token: Pre-minted API token for extension auto-login

        Returns:
            ProvisionResult with user and workspace info

        Raises:
            CoderWorkspaceExistsError: If a workspace with this name exists but
                was created from a different template
        """
        # Username is required - must be user's UUID (will be sanitized to u{uuid} format)
        if not username:
            raise ValueError(
                "username is required for workspace provisioning. "
                "Must be the backend user's UUID (str(user.id))."
            )

        # Sanitize username for Coder requirements (UUID -> u{uuid} format)
        username = self._sanitize_username(username)

        template = template or self.settings.default_template

        # Get or create user (random password - never used, auth is via ForwardAuth)
        user_data = CoderUserCreate(
            username=username,
            email=user_email,
            password=_generate_coder_password(),
            full_name=full_name,
        )
        user, user_created = await self.get_or_create_user(user_data)

        # Workspace names are scoped per user; default is derived from the
        # template so each template maps to its own workspace.
        if workspace_name:
            workspace_name = sanitize_workspace_name(workspace_name)
        else:
            workspace_name = derive_workspace_name(template)
        workspace = None
        workspace_created = False

        try:
            details = await self.get_workspace(user.username, workspace_name)
            workspace = details.workspace
            # Re-provisioning refreshes the existing workspace's token — it must
            # not silently rebuild a workspace of a DIFFERENT template.
            if workspace.template_name and workspace.template_name != template:
                raise CoderWorkspaceExistsError(
                    workspace_name,
                    detail=(
                        f"Workspace '{workspace_name}' already exists with template "
                        f"'{workspace.template_name}'. Delete it or choose another name."
                    ),
                )
            if computor_auth_token:
                logger.info(f"Workspace exists, updating with new token (prefix: {computor_auth_token[:15]}...)")
                updated = await self._update_workspace_token(
                    workspace.id,
                    computor_auth_token,
                )
                if not updated:
                    # The old token was already rotated out — a workspace left
                    # on it cannot authenticate. Fail the provision so callers
                    # can roll the rotation back instead of reporting success.
                    raise CoderWorkspaceActionError(
                        "update the auth token of",
                        workspace_name,
                        reason="token-update build could not be started",
                    )
        except CoderWorkspaceNotFoundError:
            # Create workspace. home_mode only applies at creation — for an
            # existing workspace it is immutable and the token-update rebuild
            # preserves the original value.
            ws_data = CoderWorkspaceCreate(
                name=workspace_name,
                template=template,
                computor_auth_token=computor_auth_token,
                home_mode=home_mode,
            )
            workspace = await self.create_workspace(user.username, ws_data)
            workspace_created = True

        return ProvisionResult(
            user=user,
            workspace=workspace,
            created_user=user_created,
            created_workspace=workspace_created,
        )

    # -------------------------------------------------------------------------
    # Health check
    # -------------------------------------------------------------------------

    async def health_check(self) -> tuple[bool, Optional[str]]:
        """
        Check if Coder server is healthy.

        Returns:
            Tuple of (healthy: bool, version: Optional[str])
        """
        try:
            client = await self._ensure_client()
            resp = await client.get("/api/v2/buildinfo")

            if resp.status_code == 200:
                data = resp.json()
                return True, data.get("version")

            return False, None

        except Exception as e:
            logger.warning(f"Coder health check failed: {e}")
            return False, None

    # -------------------------------------------------------------------------
    # Initial admin setup
    # -------------------------------------------------------------------------

    async def has_initial_user(self) -> bool:
        """Check if an initial (admin) user has been created in Coder.

        Coder API semantics:
        - GET /api/v2/users/first returns 200 when admin EXISTS
        - Returns 404 when no admin has been created yet
        """
        try:
            client = await self._ensure_client()
            resp = await client.get("/api/v2/users/first")
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to check initial user status: {e}")
            return False

    async def ensure_initial_admin(
        self,
        username: str,
        email: str,
        password: str,
        max_wait: int = 120,
        poll_interval: int = 2,
    ) -> bool:
        """
        Wait for Coder to be healthy, create the initial admin user if needed,
        then verify that login works with the provided credentials.

        Args:
            username: Admin username
            email: Admin email
            password: Admin password
            max_wait: Maximum seconds to wait for Coder to be ready
            poll_interval: Seconds between health check polls

        Returns:
            True if admin login succeeds
        """
        # Wait for Coder to be healthy
        waited = 0
        while waited < max_wait:
            healthy, version = await self.health_check()
            if healthy:
                logger.info(f"Coder is healthy (version: {version})")
                break
            logger.info(f"Waiting for Coder to be ready... ({waited}s/{max_wait}s)")
            await asyncio.sleep(poll_interval)
            waited += poll_interval

        if waited >= max_wait:
            logger.error(f"Coder did not become healthy after {max_wait}s")
            return False

        # Check if initial user needs to be created
        client = await self._ensure_client()

        try:
            resp = await client.get("/api/v2/users/first")
            if resp.status_code == 200:
                # 200 = initial user already exists
                logger.info("Coder initial admin already exists")
            else:
                # 404 = no initial user yet — create one
                logger.info(f"No Coder admin found (status={resp.status_code}), creating...")
                resp = await client.post(
                    "/api/v2/users/first",
                    json={
                        "username": username,
                        "email": email,
                        "password": password,
                    },
                )
                if resp.status_code == 201:
                    logger.info(f"Coder initial admin created: {username} ({email})")
                elif resp.status_code == 409:
                    logger.info("Coder admin already exists (race condition)")
                else:
                    logger.error(f"Failed to create Coder admin: status={resp.status_code}, response={resp.text}")
                    return False
        except Exception as e:
            logger.error(f"Failed during admin user check/creation: {e}")
            return False

        # Verify login actually works with the configured credentials
        try:
            resp = await client.post(
                "/api/v2/users/login",
                json={"email": email, "password": password},
            )
            if resp.status_code == 201:
                self._session_token = resp.json()["session_token"]
                logger.info("Coder admin login verified successfully")
                return True

            logger.error(
                f"Coder admin login failed — credentials in .env may not match "
                f"the existing admin user. Run wipe-coder-complete.sh to reset. "
                f"(status={resp.status_code})"
            )
            return False
        except Exception as e:
            logger.error(f"Coder admin login verification error: {e}")
            return False


# Singleton instance
_coder_client: Optional[CoderClient] = None


def get_coder_client() -> CoderClient:
    """
    Get or create the Coder client singleton.

    Returns:
        CoderClient instance
    """
    global _coder_client
    if _coder_client is None:
        _coder_client = CoderClient()
    return _coder_client


def reset_coder_client() -> None:
    """Reset the Coder client singleton."""
    global _coder_client
    _coder_client = None
