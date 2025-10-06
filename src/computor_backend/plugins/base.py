"""
Base classes and interfaces for authentication plugins.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class AuthenticationType(str, Enum):
    """Types of authentication mechanisms."""
    OAUTH2 = "oauth2"
    OIDC = "oidc"
    SAML = "saml"
    LDAP = "ldap"
    CUSTOM = "custom"


class AuthStatus(str, Enum):
    """Authentication status."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    ERROR = "error"


class UserInfo(BaseModel):
    """User information from authentication provider."""
    provider_id: str = Field(..., description="Unique user ID from provider")
    email: Optional[str] = Field(None, description="User email address")
    username: Optional[str] = Field(None, description="Username")
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")
    full_name: Optional[str] = Field(None, description="Full name")
    picture: Optional[str] = Field(None, description="Profile picture URL")
    groups: List[str] = Field(default_factory=list, description="User groups/roles")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional attributes")
    

class AuthResult(BaseModel):
    """Result of authentication attempt."""
    status: AuthStatus = Field(..., description="Authentication status")
    user_info: Optional[UserInfo] = Field(None, description="User information if successful")
    access_token: Optional[str] = Field(None, description="Access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    session_data: Dict[str, Any] = Field(default_factory=dict, description="Additional session data")


class PluginConfig(BaseModel):
    """Base configuration for plugins."""
    enabled: bool = Field(True, description="Whether plugin is enabled")
    priority: int = Field(0, description="Plugin priority (higher = higher priority)")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Plugin-specific settings")


class PluginMetadata(BaseModel):
    """Metadata about a plugin."""
    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    description: str = Field(..., description="Plugin description")
    author: Optional[str] = Field(None, description="Plugin author")
    provider_name: str = Field(..., description="Authentication provider name")
    provider_type: AuthenticationType = Field(..., description="Type of authentication")
    requires: List[str] = Field(default_factory=list, description="Required dependencies")
    homepage: Optional[str] = Field(None, description="Plugin homepage URL")


class AuthenticationPlugin(ABC):
    """
    Abstract base class for authentication plugins.
    
    All authentication plugins must inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, config: PluginConfig):
        """
        Initialize plugin with configuration.
        
        Args:
            config: Plugin configuration
        """
        self.config = config
        self._initialized = False
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass
    
    async def initialize(self) -> None:
        """
        Initialize the plugin.
        
        This method is called once when the plugin is loaded.
        Override this method to perform any initialization tasks.
        """
        self._initialized = True
    
    async def shutdown(self) -> None:
        """
        Shutdown the plugin.
        
        This method is called when the plugin is being unloaded.
        Override this method to perform any cleanup tasks.
        """
        self._initialized = False
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthResult:
        """
        Authenticate user with given credentials.
        
        Args:
            credentials: Authentication credentials (format depends on provider)
            
        Returns:
            Authentication result
        """
        pass
    
    @abstractmethod
    async def get_user_info(self, access_token: str) -> UserInfo:
        """
        Retrieve user information using access token.
        
        Args:
            access_token: Valid access token
            
        Returns:
            User information
            
        Raises:
            Exception: If token is invalid or expired
        """
        pass
    
    @abstractmethod
    def get_login_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Generate login URL for OAuth/OIDC flows.
        
        Args:
            redirect_uri: URI to redirect after authentication
            state: Optional state parameter for CSRF protection
            
        Returns:
            Login URL
        """
        pass
    
    @abstractmethod
    async def handle_callback(self, code: str, state: Optional[str] = None, redirect_uri: Optional[str] = None) -> AuthResult:
        """
        Handle OAuth/OIDC callback.
        
        Args:
            code: Authorization code from provider
            state: State parameter for CSRF validation
            redirect_uri: Redirect URI used in the original authorization request
            
        Returns:
            Authentication result
        """
        pass
    
    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New authentication result with refreshed tokens
            
        Raises:
            NotImplementedError: If provider doesn't support token refresh
        """
        raise NotImplementedError(f"Token refresh not supported by {self.metadata.provider_name}")
    
    async def logout(self, access_token: str) -> bool:
        """
        Logout user from provider.
        
        Args:
            access_token: Access token to revoke
            
        Returns:
            True if logout successful, False otherwise
        """
        # Default implementation - override if provider supports logout
        return True
    
    async def validate_token(self, access_token: str) -> bool:
        """
        Validate if access token is still valid.
        
        Args:
            access_token: Access token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        try:
            await self.get_user_info(access_token)
            return True
        except Exception:
            return False
    
    def is_initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized