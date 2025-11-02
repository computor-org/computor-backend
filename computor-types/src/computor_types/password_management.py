"""
Password management DTOs.

Request and response models for password operations including:
- Setting initial passwords
- Changing passwords
- Admin password management
"""

from pydantic import BaseModel, Field


class SetPasswordRequest(BaseModel):
    """Request to set password for first time or after reset."""
    new_password: str = Field(..., min_length=12, description="New password (min 12 chars)")
    confirm_password: str = Field(..., min_length=12, description="Confirm new password")


class ChangePasswordRequest(BaseModel):
    """Request to change user's own password."""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=12, description="New password (min 12 chars)")
    confirm_password: str = Field(..., min_length=12, description="Confirm new password")


class AdminSetPasswordRequest(BaseModel):
    """Admin request to set another user's password."""
    username: str = Field(..., description="Target username")
    new_password: str = Field(..., min_length=12, description="New password (min 12 chars)")
    confirm_password: str = Field(..., min_length=12, description="Confirm new password")
    force_reset: bool = Field(default=False, description="Require user to change password on next login")


class AdminResetPasswordRequest(BaseModel):
    """Admin request to reset a user's password (marks for reset)."""
    username: str = Field(..., description="Target username")


class PasswordStatusResponse(BaseModel):
    """Response showing password status for a user."""
    user_id: str
    username: str
    has_password: bool
    password_reset_required: bool
    password_type: str  # "argon2", "encrypted" (legacy), or "none"


class PasswordOperationResponse(BaseModel):
    """Generic response for password operations."""
    message: str
    user_id: str
    username: str
