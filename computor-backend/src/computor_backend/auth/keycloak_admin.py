"""
Keycloak Admin API client for user management.
"""

import os
import logging
from typing import Dict, Any, Optional, List
import httpx
from pydantic import BaseModel, Field

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
        """Check if a user exists in Keycloak."""
        try:
            await self._get_user_id_by_username(username)
            return True
        except ValueError:
            return False
    
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