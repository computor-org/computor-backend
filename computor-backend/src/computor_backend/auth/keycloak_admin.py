"""
Keycloak Admin API client for user management.
"""

import os
import logging
from typing import Dict, Any, Optional, List
import httpx
from pydantic import BaseModel, Field

from computor_backend.utils.git_username import username_candidates

logger = logging.getLogger(__name__)


class KeycloakUser(BaseModel):
    """Keycloak user representation."""
    username: str = Field(..., description="Username")
    email: Optional[str] = Field(None, description="Email address")
    firstName: Optional[str] = Field(None, description="First name")
    lastName: Optional[str] = Field(None, description="Last name")
    enabled: bool = Field(True, description="Whether user is enabled")
    emailVerified: bool = Field(False, description="Whether email is verified")
    credentials: Optional[List[Dict[str, Any]]] = Field(None, description="User credentials")
    attributes: Optional[Dict[str, Any]] = Field(None, description="User attributes")
    groups: Optional[List[str]] = Field(None, description="User groups")


class KeycloakAdminClient:
    """
    Keycloak Admin REST API client for user management operations.
    """
    
    def __init__(self):
        """Initialize Keycloak admin client with environment configuration."""
        self.server_url = os.environ.get("KEYCLOAK_SERVER_URL", "http://localhost:8180")
        self.realm = os.environ.get("KEYCLOAK_REALM", "computor")
        self.admin_username = os.environ.get("KEYCLOAK_ADMIN", "admin")
        self.admin_password = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin_password")
        self.client_id = os.environ.get("KEYCLOAK_CLIENT_ID", "computor-backend")
        self.client_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET", "computor-backend-secret")
        self._access_token = None
        self.verify_ssl = True
    
    async def _get_admin_token(self) -> str:
        """Get admin access token for Keycloak API operations."""
        if self._access_token:
            # TODO: Check token expiration
            return self._access_token
        
        token_url = f"{self.server_url}/realms/master/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "username": self.admin_username,
            "password": self.admin_password,
            "client_id": "admin-cli",
            "scope": "openid"
        }
        
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get admin token: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            return self._access_token
    
    async def create_user(self, user: KeycloakUser) -> str:
        """
        Create a new user in Keycloak.
        
        Returns the user ID of the created user.
        """
        token = await self._get_admin_token()
        users_url = f"{self.server_url}/admin/realms/{self.realm}/users"
        
        # Prepare user data
        user_data = user.model_dump(exclude_none=True)
        
        # Set temporary password if provided
        if user.credentials:
            user_data["credentials"] = user.credentials
        else:
            # Generate a temporary password that must be changed on first login
            user_data["credentials"] = [{
                "type": "password",
                "value": "TempPassword123!",
                "temporary": True
            }]
        
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.post(
                users_url,
                json=user_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 409:
                raise ValueError(f"User already exists: {user.username}")
            
            if response.status_code != 201:
                logger.error(f"Failed to create user: {response.status_code} - {response.text}")
                response.raise_for_status()
            
            # Extract user ID from Location header
            location_header = response.headers.get("Location")
            if location_header:
                user_id = location_header.split("/")[-1]
                logger.info(f"Created Keycloak user: {user.username} (ID: {user_id})")
                return user_id
            
            # If no Location header, fetch the user to get ID
            return await self._get_user_id_by_username(user.username)
    
    async def _get_user_id_by_username(self, username: str) -> str:
        """Get user ID by username."""
        token = await self._get_admin_token()
        users_url = f"{self.server_url}/admin/realms/{self.realm}/users"
        
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.get(
                users_url,
                params={"username": username, "exact": "true"},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code != 200:
                response.raise_for_status()
            
            users = response.json()
            if not users:
                raise ValueError(f"User not found: {username}")
            
            return users[0]["id"]
    
    async def user_exists(self, username: str) -> bool:
        """Check if a user exists in Keycloak (by username)."""
        try:
            await self._get_user_id_by_username(username)
            return True
        except ValueError:
            return False

    async def _get_user_id_by_email(self, email: str) -> Optional[str]:
        """Return the Keycloak user id for an exact email match, or None.

        Safe to treat as unique: the realm sets ``duplicateEmailsAllowed=false``.
        This is the cross-system matching key now that the Keycloak username is a
        generated handle rather than the email.
        """
        token = await self._get_admin_token()
        users_url = f"{self.server_url}/admin/realms/{self.realm}/users"

        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.get(
                users_url,
                params={"email": email, "exact": "true"},
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code != 200:
                response.raise_for_status()
            users = response.json()
            return users[0]["id"] if users else None

    async def user_exists_by_email(self, email: str) -> bool:
        """Check if a user exists in Keycloak (by email)."""
        return await self._get_user_id_by_email(email) is not None

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Return the full Keycloak user representation, or None if absent."""
        token = await self._get_admin_token()
        user_url = f"{self.server_url}/admin/realms/{self.realm}/users/{user_id}"

        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.get(
                user_url, headers={"Authorization": f"Bearer {token}"}
            )
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                response.raise_for_status()
            return response.json()

    async def get_username(self, user_id: str) -> Optional[str]:
        """Return the current Keycloak username for a user id (authoritative live read)."""
        user = await self.get_user(user_id)
        return user.get("username") if user else None

    async def generate_unique_username(
        self,
        given_name: Optional[str],
        family_name: Optional[str],
        email: Optional[str] = None,
    ) -> str:
        """Pick the first Forgejo-safe candidate handle not taken in Keycloak.

        Candidates come from the user's name (falling back to the email
        local-part); if every candidate collides, a numeric suffix is appended.
        Keycloak enforces realm-wide username uniqueness, so the chosen handle is
        safe to use as the Forgejo account name.
        """
        candidates = username_candidates(given_name, family_name, email)
        for candidate in candidates:
            if not await self.user_exists(candidate):
                return candidate

        base = candidates[0]
        suffix = 2
        while await self.user_exists(f"{base}{suffix}"):
            suffix += 1
            if suffix > 9999:
                raise ValueError(
                    f"Could not allocate a unique username from base '{base}'"
                )
        return f"{base}{suffix}"
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing user in Keycloak."""
        token = await self._get_admin_token()
        user_url = f"{self.server_url}/admin/realms/{self.realm}/users/{user_id}"
        
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.put(
                user_url,
                json=updates,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code not in (200, 204):
                logger.error(f"Failed to update user: {response.status_code} - {response.text}")
                response.raise_for_status()
    
    async def set_user_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Set user password in Keycloak."""
        token = await self._get_admin_token()
        password_url = f"{self.server_url}/admin/realms/{self.realm}/users/{user_id}/reset-password"
        
        credential_data = {
            "type": "password",
            "value": password,
            "temporary": temporary
        }
        
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.put(
                password_url,
                json=credential_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code not in (200, 204):
                logger.error(f"Failed to set password: {response.status_code} - {response.text}")
                response.raise_for_status()
    
    async def add_user_to_group(self, user_id: str, group_id: str) -> None:
        """Add user to a Keycloak group."""
        token = await self._get_admin_token()
        group_url = f"{self.server_url}/admin/realms/{self.realm}/users/{user_id}/groups/{group_id}"
        
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.put(
                group_url,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code not in (200, 204):
                logger.error(f"Failed to add user to group: {response.status_code} - {response.text}")
                response.raise_for_status()
    
    async def get_group_id(self, name: str) -> Optional[str]:
        """Return the id of a top-level realm group by exact name, or None."""
        token = await self._get_admin_token()
        groups_url = f"{self.server_url}/admin/realms/{self.realm}/groups"

        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.get(
                groups_url,
                params={"search": name},
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code != 200:
                response.raise_for_status()
            for group in response.json():
                if group.get("name") == name:
                    return group["id"]
        return None

    async def delete_user(self, user_id: str) -> None:
        """Delete a user from Keycloak."""
        token = await self._get_admin_token()
        user_url = f"{self.server_url}/admin/realms/{self.realm}/users/{user_id}"
        
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.delete(
                user_url,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code not in (200, 204):
                logger.error(f"Failed to delete user: {response.status_code} - {response.text}")
                response.raise_for_status()
    
    async def ensure_client_redirect_uris(self, redirect_uris: list[str], web_origins: list[str], client_id: str | None = None) -> None:
        """Add the given redirect URIs and web origins to a Keycloak client (idempotent).

        Defaults to this deployment's backend client (self.client_id); pass client_id
        to reconcile a different client — e.g. the 'forgejo' OIDC client, whose redirect
        URI otherwise goes stale when FORGEJO_ROOT_URL changes (the busybox-based
        forgejo setup script can only POST-create, never update an existing client).

        For the backend client, pass both the login callback and the app-root URI: its
        post.logout.redirect.uris is "+", meaning it reuses the valid redirect URIs, so
        the app-root entry is also what makes logout's post_logout_redirect_uri accepted.
        """
        target_client_id = client_id or self.client_id
        token = await self._get_admin_token()
        clients_url = f"{self.server_url}/admin/realms/{self.realm}/clients"

        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            resp = await client.get(
                clients_url,
                params={"clientId": target_client_id, "search": "false"},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            clients = resp.json()
            if not clients:
                logger.warning(f"Keycloak client '{target_client_id}' not found — skipping redirect URI registration")
                return

            kc_client = clients[0]
            internal_id = kc_client["id"]
            current_uris = set(kc_client.get("redirectUris", []))
            current_origins = set(kc_client.get("webOrigins", []))

            merged_uris = current_uris | set(redirect_uris)
            merged_origins = current_origins | set(web_origins)

            if merged_uris == current_uris and merged_origins == current_origins:
                return  # nothing new to add

            updated = {
                "redirectUris": sorted(merged_uris),
                "webOrigins": sorted(merged_origins),
            }
            put_resp = await client.put(
                f"{clients_url}/{internal_id}",
                json={**kc_client, **updated},
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            if put_resp.status_code not in (200, 204):
                logger.error(f"Failed to update client redirect URIs: {put_resp.status_code} - {put_resp.text}")
                put_resp.raise_for_status()
            logger.info(f"Ensured redirect URIs {sorted(set(redirect_uris))} on Keycloak client '{target_client_id}'")

    async def send_verify_email(self, user_id: str) -> None:
        """Send email verification to user."""
        token = await self._get_admin_token()
        email_url = f"{self.server_url}/admin/realms/{self.realm}/users/{user_id}/send-verify-email"
        
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.put(
                email_url,
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code not in (200, 204):
                logger.error(f"Failed to send verify email: {response.status_code} - {response.text}")
                response.raise_for_status()