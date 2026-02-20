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
    CoderWorkspaceExistsError,
    CoderWorkspaceNotFoundError,
)
from .schemas import (
    CoderTemplate,
    CoderUser,
    CoderUserCreate,
    CoderWorkspace,
    CoderWorkspaceCreate,
    ProvisionResult,
    WorkspaceDetails,
    WorkspaceStatus,
    WorkspaceTemplate,
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

        token = await self._get_session_token()
        client = await self._ensure_client()

        resp = await client.get(
            "/api/v2/organizations",
            headers={"Coder-Session-Token": token},
        )

        if resp.status_code != 200:
            raise CoderAPIError(
                "Failed to get organizations",
                status_code=resp.status_code,
            )

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
        token = await self._get_session_token()
        client = await self._ensure_client()

        # Try by username first
        resp = await client.get(
            f"/api/v2/users/{username_or_email}",
            headers={"Coder-Session-Token": token},
        )

        if resp.status_code == 200:
            data = resp.json()
            return CoderUser(
                id=data["id"],
                username=data["username"],
                email=data["email"],
                name=data.get("name"),
                created_at=data.get("created_at"),
                status=data.get("status"),
            )

        # If not found and looks like email, search by email
        if resp.status_code == 404 and "@" in username_or_email:
            return await self._find_user_by_email(username_or_email)

        raise CoderUserNotFoundError(username_or_email)

    async def _find_user_by_email(self, email: str) -> CoderUser:
        """Find user by email address."""
        token = await self._get_session_token()
        client = await self._ensure_client()

        # List users and filter by email
        resp = await client.get(
            "/api/v2/users",
            headers={"Coder-Session-Token": token},
            params={"q": email},
        )

        if resp.status_code != 200:
            raise CoderAPIError(
                "Failed to search users",
                status_code=resp.status_code,
            )

        data = resp.json()
        users = data.get("users", [])

        for user in users:
            if user.get("email", "").lower() == email.lower():
                return CoderUser(
                    id=user["id"],
                    username=user["username"],
                    email=user["email"],
                    name=user.get("name"),
                    created_at=user.get("created_at"),
                    status=user.get("status"),
                )

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
        token = await self._get_session_token()
        org_id = await self._get_org_id()
        client = await self._ensure_client()

        payload: dict[str, Any] = {
            "username": user_data.username,
            "email": user_data.email,
            "password": user_data.password,
            "user_status": "active",
            "organization_ids": [org_id],
        }

        if user_data.full_name:
            payload["name"] = user_data.full_name

        resp = await client.post(
            "/api/v2/users",
            headers=self._get_headers(token),
            json=payload,
        )

        if resp.status_code == 409:
            raise CoderUserExistsError(user_data.email)

        if resp.status_code not in (200, 201):
            logger.error(f"Coder API user creation failed: status={resp.status_code}, response={resp.text}")
            raise CoderAPIError(
                f"Failed to create user '{user_data.username}': {resp.text}",
                status_code=resp.status_code,
                detail=resp.text,
            )

        data = resp.json()
        logger.info(f"Created Coder user: {user_data.username}")

        return CoderUser(
            id=data["id"],
            username=data["username"],
            email=data["email"],
            name=data.get("name"),
            created_at=data.get("created_at"),
            status=data.get("status"),
        )

    async def update_user_password(self, username: str, new_password: str) -> bool:
        """
        Update a user's password.

        Args:
            username: Username of the user
            new_password: New password to set

        Returns:
            True if password was updated successfully
        """
        token = await self._get_session_token()
        client = await self._ensure_client()

        # Try the standard password update endpoint
        resp = await client.put(
            f"/api/v2/users/{username}/password",
            headers=self._get_headers(token),
            json={"password": new_password, "old_password": ""},
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
        token = await self._get_session_token()
        client = await self._ensure_client()

        resp = await client.post(
            f"/api/v2/users/{username}/keys",
            headers=self._get_headers(token),
            json={"lifetime_seconds": 86400 * 7},  # 7 days
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
        token = await self._get_session_token()
        client = await self._ensure_client()

        resp = await client.delete(
            f"/api/v2/users/{username}",
            headers=self._get_headers(token),
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
        token = await self._get_session_token()
        client = await self._ensure_client()

        resp = await client.get(
            "/api/v2/templates",
            headers={"Coder-Session-Token": token},
        )

        if resp.status_code != 200:
            raise CoderAPIError(
                "Failed to list templates",
                status_code=resp.status_code,
            )

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

    # -------------------------------------------------------------------------
    # Workspace operations
    # -------------------------------------------------------------------------

    async def get_workspace(
        self,
        username: str,
        workspace_name: Optional[str] = None,
    ) -> WorkspaceDetails:
        """
        Get workspace details for a user.

        Args:
            username: User's username
            workspace_name: Workspace name (defaults to {username}-workspace)

        Returns:
            WorkspaceDetails instance

        Raises:
            CoderWorkspaceNotFoundError: If workspace not found
        """
        token = await self._get_session_token()
        client = await self._ensure_client()

        workspace_name = workspace_name or f"{username}-workspace"

        resp = await client.get(
            f"/api/v2/users/{username}/workspace/{workspace_name}",
            headers={"Coder-Session-Token": token},
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
        token = await self._get_session_token()
        client = await self._ensure_client()

        resp = await client.get(
            f"/api/v2/workspaces",
            headers={"Coder-Session-Token": token},
            params={"q": f"owner:{username}"},
        )

        if resp.status_code != 200:
            raise CoderAPIError(
                f"Failed to list workspaces for user {username}",
                status_code=resp.status_code,
            )

        data = resp.json()
        workspaces = data.get("workspaces", [])

        return [
            CoderWorkspace(
                id=ws["id"],
                name=ws["name"],
                owner_id=ws["owner_id"],
                owner_name=ws.get("owner_name"),
                template_id=ws["template_id"],
                template_name=ws.get("template_display_name") or ws.get("template_name"),
                latest_build_status=ws.get("latest_build", {}).get("status"),
                created_at=ws.get("created_at"),
                updated_at=ws.get("updated_at"),
            )
            for ws in workspaces
        ]

    async def workspace_exists(
        self,
        username: str,
        workspace_name: Optional[str] = None,
    ) -> bool:
        """
        Check if a workspace exists for a user.

        Args:
            username: User's username
            workspace_name: Workspace name (defaults to {username}-workspace)

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
        token = await self._get_session_token()
        template_id = await self.get_template_id(workspace_data.template.value)
        client = await self._ensure_client()

        workspace_name = workspace_data.name or f"{username}-workspace"

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
        if rich_params:
            payload["rich_parameter_values"] = rich_params
            logger.info(f"Sending rich_parameter_values: {[p['name'] for p in rich_params]}")

        resp = await client.post(
            f"/api/v2/organizations/default/members/{username}/workspaces",
            headers=self._get_headers(token),
            json=payload,
            timeout=self.settings.workspace_timeout,
        )

        if resp.status_code == 409:
            raise CoderWorkspaceExistsError(workspace_name)

        if resp.status_code not in (200, 201):
            logger.error(f"Coder API workspace creation failed: status={resp.status_code}, response={resp.text}")
            raise CoderAPIError(
                f"Failed to create workspace '{workspace_name}': {resp.text}",
                status_code=resp.status_code,
                detail=resp.text,
            )

        data = resp.json()
        logger.info(f"Created workspace: {workspace_name} for user {username}")

        return CoderWorkspace(
            id=data["id"],
            name=data["name"],
            owner_id=data["owner_id"],
            owner_name=data.get("owner_name"),
            template_id=data["template_id"],
            template_name=data.get("template_display_name") or data.get("template_name"),
            latest_build_status=data.get("latest_build", {}).get("status"),
            created_at=data.get("created_at"),
        )

    async def delete_workspace(
        self,
        username: str,
        workspace_name: Optional[str] = None,
    ) -> bool:
        """
        Delete a workspace.

        Args:
            username: User's username
            workspace_name: Workspace name (defaults to {username}-workspace)

        Returns:
            True if deleted successfully
        """
        token = await self._get_session_token()
        client = await self._ensure_client()

        workspace_name = workspace_name or f"{username}-workspace"
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
        resp = await client.post(
            f"/api/v2/workspaces/{details.workspace.id}/builds",
            headers=self._get_headers(token),
            json={"transition": "delete"},
        )

        if resp.status_code in (200, 201, 202):
            logger.info(f"Delete build started for workspace: {workspace_name} (status={resp.status_code})")
            return True

        logger.error(f"Failed to delete workspace {workspace_name}: status={resp.status_code}, response={resp.text}")
        return False

    async def start_workspace(
        self,
        username: str,
        workspace_name: Optional[str] = None,
    ) -> bool:
        """
        Start a stopped workspace.

        Args:
            username: User's username
            workspace_name: Workspace name (defaults to {username}-workspace)

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
        workspace_name: Optional[str] = None,
    ) -> bool:
        """
        Stop a running workspace.

        Args:
            username: User's username
            workspace_name: Workspace name (defaults to {username}-workspace)

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
        token = await self._get_session_token()
        client = await self._ensure_client()

        # Get workspace to find template version
        resp = await client.get(
            f"/api/v2/workspaces/{workspace_id}",
            headers={"Coder-Session-Token": token},
        )

        if resp.status_code != 200:
            return False

        workspace = resp.json()
        template_version_id = workspace["latest_build"]["template_version_id"]

        # Create transition build
        resp = await client.post(
            f"/api/v2/workspaces/{workspace_id}/builds",
            headers={"Coder-Session-Token": token},
            json={
                "template_version_id": template_version_id,
                "transition": transition,
            },
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
            template_name=data.get("template_display_name") or data.get("template_name"),
            latest_build_status=data.get("latest_build", {}).get("status"),
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

        # Build access URL for running workspaces (URL is deterministic)
        if status == WorkspaceStatus.RUNNING and self.settings.url:
            access_url = f"{self.settings.url}/@{data.get('owner_name', '')}/{data['name']}"

        # Extract code-server URL from agent apps
        logger.info(f"Parsing workspace resources: {len(latest_build.get('resources', []))} resources")
        for resource in latest_build.get("resources", []):
            resource_name = resource.get("name", "unknown")
            agents = resource.get("agents", [])
            logger.info(f"Resource '{resource_name}' has {len(agents)} agents")

            for agent in agents:
                agent_name = agent.get("name", "unknown")
                agent_status = agent.get("status")
                apps = agent.get("apps", [])
                logger.info(f"Agent '{agent_name}' status={agent_status}, apps count={len(apps)}")

                # Store agent info in resources
                resources[agent_name] = {
                    "status": agent_status,
                    "apps": [app.get("slug") for app in apps],
                }

                # Look for code-server app (check multiple possible slugs)
                for app in apps:
                    app_slug = app.get("slug", "").lower()
                    app_url = app.get("url")
                    logger.info(f"App: slug='{app_slug}', url={app_url}")

                    if any(term in app_slug for term in ["code", "vscode", "vs-code"]):
                        # Skip localhost URLs - they're internal container URLs not accessible from outside
                        if app_url and "localhost" not in app_url and "127.0.0.1" not in app_url:
                            code_server_url = app_url
                            logger.info(f"Found code-server URL: {code_server_url}")
                        else:
                            logger.info(f"Skipping internal URL: {app_url}")
                        break

        # Generate code-server URL for running workspaces
        if status == WorkspaceStatus.RUNNING and not code_server_url:
            owner_name = data.get("owner_name", "")
            workspace_name = data["name"]

            # Prefer Traefik URL if configured (bypasses Coder proxy)
            if self.settings.workspace_base_url:
                base_url = self.settings.workspace_base_url.rstrip("/")
                code_server_url = f"{base_url}/{owner_name}/{workspace_name}/"
                logger.info(f"Using Traefik code-server URL: {code_server_url}")
            elif access_url:
                # Fallback: Coder app proxy path
                code_server_url = f"{access_url}/apps/code-server/"
                logger.info(f"Using Coder proxy code-server URL: {code_server_url}")

        logger.info(f"Workspace details: status={status}, access_url={access_url}, code_server_url={code_server_url}")

        return WorkspaceDetails(
            workspace=workspace,
            status=status,
            access_url=access_url,
            code_server_url=code_server_url,
            health=data.get("health", {}).get("healthy"),
            resources=resources,
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
        token = await self._get_session_token()
        client = await self._ensure_client()

        # Get workspace to find template version
        resp = await client.get(
            f"/api/v2/workspaces/{workspace_id}",
            headers={"Coder-Session-Token": token},
        )

        if resp.status_code != 200:
            logger.error(f"Failed to get workspace for token update: {resp.status_code}")
            return False

        workspace = resp.json()
        template_version_id = workspace["latest_build"]["template_version_id"]

        # Create a new build with the updated token parameter
        rich_params = [{
            "name": "computor_auth_token",
            "value": computor_auth_token,
        }]

        resp = await client.post(
            f"/api/v2/workspaces/{workspace_id}/builds",
            headers=self._get_headers(token),
            json={
                "template_version_id": template_version_id,
                "transition": "start",
                "rich_parameter_values": rich_params,
            },
            timeout=self.settings.workspace_timeout,
        )

        success = resp.status_code in (200, 201)
        if success:
            print(f"[CODER] Token update build initiated for workspace {workspace_id}")
            logger.info(f"Workspace {workspace_id}: token update build initiated")
        else:
            print(f"[CODER] FAILED to update token: {resp.status_code} - {resp.text}")
            logger.error(f"Failed to update workspace token: {resp.status_code} - {resp.text}")
        return success

    # -------------------------------------------------------------------------
    # Provisioning (combined user + workspace)
    # -------------------------------------------------------------------------

    async def provision_workspace(
        self,
        user_email: str,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        template: WorkspaceTemplate = WorkspaceTemplate.PYTHON,
        workspace_name: Optional[str] = None,
        computor_auth_token: Optional[str] = None,
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
            template: Workspace template to use
            workspace_name: Custom workspace name
            computor_auth_token: Pre-minted API token for extension auto-login

        Returns:
            ProvisionResult with user and workspace info
        """
        # Username is required - must be user's UUID (will be sanitized to u{uuid} format)
        if not username:
            raise ValueError(
                "username is required for workspace provisioning. "
                "Must be the backend user's UUID (str(user.id))."
            )

        # Sanitize username for Coder requirements (UUID -> u{uuid} format)
        username = self._sanitize_username(username)

        # Get or create user (random password - never used, auth is via ForwardAuth)
        user_data = CoderUserCreate(
            username=username,
            email=user_email,
            password=_generate_coder_password(),
            full_name=full_name,
        )
        user, user_created = await self.get_or_create_user(user_data)

        # Check if workspace already exists
        # Workspace names are scoped per user, so we use a simple default name
        # Coder workspace names also have length limits (~32 chars)
        if not workspace_name:
            workspace_name = "workspace"
        # Sanitize workspace name (NO 'u' prefix - that's only for usernames)
        import re
        workspace_name = re.sub(r"[^a-z0-9-]", "", workspace_name.lower())[:32].rstrip("-")
        workspace = None
        workspace_created = False

        try:
            details = await self.get_workspace(user.username, workspace_name)
            workspace = details.workspace
            # Workspace exists - update it with new token by triggering a rebuild
            if computor_auth_token:
                print(f"[CODER] Workspace exists, updating with new token (prefix: {computor_auth_token[:15]}...)")
                logger.info(f"Workspace exists, updating with new token...")
                await self._update_workspace_token(
                    workspace.id,
                    computor_auth_token,
                )
        except CoderWorkspaceNotFoundError:
            # Create workspace
            ws_data = CoderWorkspaceCreate(
                name=workspace_name,
                template=template,
                computor_auth_token=computor_auth_token,
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
        """Check if an initial (admin) user has been created in Coder."""
        try:
            client = await self._ensure_client()
            resp = await client.get("/api/v2/users/first")
            # 200 means no initial user yet (returns the form)
            # Coder returns 200 when first user has NOT been created
            # and a redirect/different status when it HAS been created
            # Actually the semantics: if the endpoint returns successfully,
            # it means we can still create the first user (none exists).
            # A non-success status means one already exists.
            return resp.status_code != 200
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
        Wait for Coder to be healthy, then create the initial admin user
        if one doesn't exist yet via POST /api/v2/users/first.

        Args:
            username: Admin username
            email: Admin email
            password: Admin password
            max_wait: Maximum seconds to wait for Coder to be ready
            poll_interval: Seconds between health check polls

        Returns:
            True if admin was created or already exists
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

        # Check if initial user already exists
        client = await self._ensure_client()

        try:
            resp = await client.get("/api/v2/users/first")
            if resp.status_code != 200:
                # Initial user already exists
                logger.info("Coder initial admin user already exists")
                return True
        except Exception as e:
            logger.error(f"Failed to check initial user: {e}")
            return False

        # Create initial admin user
        try:
            resp = await client.post(
                "/api/v2/users/first",
                json={
                    "username": username,
                    "email": email,
                    "password": password,
                },
            )

            if resp.status_code == 201:
                logger.info(f"Coder initial admin user created: {username} ({email})")
                return True

            # 409 or similar — already exists (race condition)
            if resp.status_code in (409, 400):
                logger.info(f"Coder admin user already exists (status {resp.status_code})")
                return True

            logger.error(
                f"Failed to create Coder initial admin: "
                f"status={resp.status_code}, response={resp.text}"
            )
            return False

        except Exception as e:
            logger.error(f"Exception creating Coder initial admin: {e}")
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
