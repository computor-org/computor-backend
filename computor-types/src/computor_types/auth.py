from abc import ABC
from typing import Optional
from pydantic import BaseModel, Field
from computor_types.deployments import BaseDeployment

class AuthConfig(ABC, BaseDeployment):
    pass

class GLPAuthConfig(AuthConfig):
    url: str
    token: str

class BasicAuthConfig(AuthConfig):
    username: str
    password: str

# Local authentication DTOs

class LocalLoginRequest(BaseModel):
    """Request model for local username/password login."""
    username: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=1, description="Password")

class LocalLoginResponse(BaseModel):
    """Response model after successful local login."""
    access_token: str = Field(..., description="Bearer access token for API requests")
    refresh_token: str = Field(..., description="Refresh token to obtain new access token")
    expires_in: int = Field(..., description="Access token expiration time in seconds")
    user_id: str = Field(..., description="User ID")
    token_type: str = Field(default="Bearer", description="Token type")

class LogoutRequest(BaseModel):
    """Request model for logout."""
    provider: Optional[str] = Field(None, description="Provider name for SSO logout (optional)")

class LogoutResponse(BaseModel):
    """Response model after successful logout."""
    message: str = Field(..., description="Logout status message")
    provider: Optional[str] = Field(None, description="Provider that was logged out from")

class LocalTokenRefreshRequest(BaseModel):
    """Request model for refreshing local session token."""
    refresh_token: str = Field(..., description="Refresh token from initial authentication")

class LocalTokenRefreshResponse(BaseModel):
    """Response model after successful token refresh."""
    access_token: str = Field(..., description="New Bearer access token")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    refresh_token: Optional[str] = Field(None, description="New refresh token if rotated")
    token_type: str = Field(default="Bearer", description="Token type")