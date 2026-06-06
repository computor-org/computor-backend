from abc import ABC
from typing import Optional
from pydantic import BaseModel, Field
from computor_types.deployments_refactored import BaseDeployment

class AuthConfig(ABC, BaseDeployment):
    pass

class GLPAuthConfig(AuthConfig):
    url: str
    token: str

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


# SSO/Provider authentication DTOs

class ProviderInfo(BaseModel):
    """Information about an authentication provider."""
    name: str = Field(..., description="Provider name")
    display_name: str = Field(..., description="Display name")
    type: str = Field(..., description="Authentication type")
    enabled: bool = Field(..., description="Whether provider is enabled")
    login_url: Optional[str] = Field(None, description="Login URL if applicable")


class LoginRequest(BaseModel):
    """Login request for SSO."""
    provider: str = Field(..., description="Provider name")
    redirect_uri: Optional[str] = Field(None, description="Redirect URI after login")


class UserRegistrationRequest(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    given_name: str = Field(..., min_length=1, description="First name")
    family_name: str = Field(..., min_length=1, description="Last name")
    provider: str = Field("keycloak", description="Authentication provider to register with")
    send_verification_email: bool = Field(True, description="Send email verification")


class UserRegistrationResponse(BaseModel):
    """Response after successful user registration."""
    user_id: str = Field(..., description="User ID in Computor")
    provider_user_id: str = Field(..., description="User ID in authentication provider")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    message: str = Field(..., description="Success message")


class TokenRefreshRequest(BaseModel):
    """Token refresh request for SSO."""
    refresh_token: str = Field(..., description="Refresh token from initial authentication")
    provider: str = Field("keycloak", description="Authentication provider")


class TokenRefreshResponse(BaseModel):
    """Response after successful SSO token refresh."""
    access_token: str = Field(..., description="New access token")
    expires_in: Optional[int] = Field(None, description="Token expiration time in seconds")
    refresh_token: Optional[str] = Field(None, description="New refresh token if rotated")


class GitLabRegisterRequest(BaseModel):
    """Self-service migration: set a Keycloak password, gated by a GitLab PAT.

    The PAT proves the caller controls a GitLab account whose email matches an
    existing computor user (by User.email or the org-scoped StudentProfile email).
    No password is read from our database (local auth is gone); the PAT is only
    used for verification and is never stored.
    """
    gitlab_url: str = Field(..., description="GitLab instance URL the PAT was issued on")
    gitlab_pat: str = Field(..., description="GitLab Personal Access Token (verification only, not stored)")
    new_password: str = Field(..., description="Password to set for Keycloak login")


class GitLabRegisterResponse(BaseModel):
    """Response after provisioning/resetting a Keycloak login via GitLab PAT."""
    user_id: str = Field(..., description="User ID in Computor")
    email: str = Field(..., description="Email address (Keycloak username)")
    created: bool = Field(..., description="True if the Keycloak user was created, False if its password was reset")