"""
Password reset and management endpoints.

This module provides endpoints for:
- Setting initial passwords (after admin creates account)
- Changing passwords (user changes own password)
- Admin-initiated password resets
- Password reset token generation and validation (future)
"""

import logging
from typing import Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr

from computor_backend.database import get_db
from computor_backend.model.auth import User
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.api.exceptions import (
    NotFoundException,
    BadRequestException,
    ForbiddenException,
)
from computor_backend.business_logic.users import set_user_password
from computor_types.password_utils import PasswordValidationError
from computor_types.password_management import (
    SetPasswordRequest,
    ChangePasswordRequest,
    AdminSetPasswordRequest,
    AdminResetPasswordRequest,
    PasswordStatusResponse,
    PasswordOperationResponse,
)

logger = logging.getLogger(__name__)

password_reset_router = APIRouter(prefix="/password", tags=["password-management"])


# Endpoints

@password_reset_router.get("/status", response_model=PasswordStatusResponse)
async def get_password_status(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> PasswordStatusResponse:
    """
    Get password status for current user.

    Returns information about password state:
    - Whether password is set
    - Whether password reset is required
    - Type of password (Argon2, legacy encrypted, or none)
    """
    user = db.query(User).filter(User.id == principal.user_id).first()
    if not user:
        raise NotFoundException("User not found")

    from computor_types.password_utils import is_argon2_hash

    has_password = user.password is not None
    password_type = "none"

    if has_password:
        if is_argon2_hash(user.password):
            password_type = "argon2"
        else:
            password_type = "encrypted"  # Legacy

    return PasswordStatusResponse(
        user_id=str(user.id),
        username=user.username,
        has_password=has_password,
        password_reset_required=user.password_reset_required or False,
        password_type=password_type,
    )


@password_reset_router.post("/set", response_model=PasswordOperationResponse)
async def set_initial_password(
    request: SetPasswordRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> PasswordOperationResponse:
    """
    Set password for first time or after admin reset.

    Use this endpoint when:
    - User logging in for first time (password_reset_required = true)
    - Admin reset user's password
    - User has no password set

    This endpoint does NOT require old password.
    """
    user = db.query(User).filter(User.id == principal.user_id).first()
    if not user:
        raise NotFoundException("User not found")

    # Validate passwords match
    if request.new_password != request.confirm_password:
        raise BadRequestException("Passwords do not match")

    # Use the business logic function (it will validate complexity)
    try:
        # For initial password set, we don't need old password
        # Pass None for both target_username and old_password, but use the user_id
        user.password = None  # Ensure old password check is skipped
        set_user_password(
            target_username=user.username,  # Admin setting password (but for self in this case)
            new_password=request.new_password,
            old_password=None,
            permissions=principal,
            db=db,
        )
    except PasswordValidationError as e:
        raise BadRequestException(str(e))

    logger.info(f"Initial password set for user {user.username} (ID: {user.id})")

    return PasswordOperationResponse(
        message="Password set successfully",
        user_id=str(user.id),
        username=user.username,
    )


@password_reset_router.post("/change", response_model=PasswordOperationResponse)
async def change_password(
    request: ChangePasswordRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> PasswordOperationResponse:
    """
    Change user's own password.

    Requires current password for verification.
    User must know their current password.
    """
    user = db.query(User).filter(User.id == principal.user_id).first()
    if not user:
        raise NotFoundException("User not found")

    # Validate passwords match
    if request.new_password != request.confirm_password:
        raise BadRequestException("Passwords do not match")

    # Use business logic function
    try:
        set_user_password(
            target_username=None,  # User changing own password
            new_password=request.new_password,
            old_password=request.old_password,
            permissions=principal,
            db=db,
        )
    except PasswordValidationError as e:
        raise BadRequestException(str(e))

    logger.info(f"Password changed for user {user.username} (ID: {user.id})")

    return PasswordOperationResponse(
        message="Password changed successfully",
        user_id=str(user.id),
        username=user.username,
    )


@password_reset_router.post("/admin/set", response_model=PasswordOperationResponse)
async def admin_set_password(
    request: AdminSetPasswordRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> PasswordOperationResponse:
    """
    Admin endpoint to set another user's password.

    Requires admin privileges.
    Optionally can force user to change password on next login.
    """
    if not principal.is_admin:
        raise ForbiddenException("Only administrators can set other users' passwords")

    target_user = db.query(User).filter(User.username == request.username).first()
    if not target_user:
        raise NotFoundException(f"User '{request.username}' not found")

    # Validate passwords match
    if request.new_password != request.confirm_password:
        raise BadRequestException("Passwords do not match")

    # Use business logic function
    try:
        set_user_password(
            target_username=request.username,
            new_password=request.new_password,
            old_password=None,  # Admin doesn't need old password
            permissions=principal,
            db=db,
        )

        # Set force_reset flag if requested
        if request.force_reset:
            target_user.password_reset_required = True
            db.commit()

    except PasswordValidationError as e:
        raise BadRequestException(str(e))

    logger.info(
        f"Admin {principal.user_id} set password for user {target_user.username} "
        f"(force_reset={request.force_reset})"
    )

    return PasswordOperationResponse(
        message=f"Password set for user '{request.username}'" +
                (" (reset required on next login)" if request.force_reset else ""),
        user_id=str(target_user.id),
        username=target_user.username,
    )


@password_reset_router.post("/admin/reset", response_model=PasswordOperationResponse)
async def admin_reset_password(
    request: AdminResetPasswordRequest,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> PasswordOperationResponse:
    """
    Admin endpoint to invalidate user's password and require reset.

    This does NOT set a new password, it:
    1. Marks password as requiring reset
    2. User must use password reset flow or admin must set new password

    Requires admin privileges.
    """
    if not principal.is_admin:
        raise ForbiddenException("Only administrators can reset passwords")

    target_user = db.query(User).filter(User.username == request.username).first()
    if not target_user:
        raise NotFoundException(f"User '{request.username}' not found")

    # Mark for password reset
    target_user.password_reset_required = True
    db.commit()

    logger.info(f"Admin {principal.user_id} marked {target_user.username} for password reset")

    return PasswordOperationResponse(
        message=f"Password reset required for user '{request.username}'. "
                "User must contact administrator or use password reset link.",
        user_id=str(target_user.id),
        username=target_user.username,
    )


@password_reset_router.get("/admin/status/{username}", response_model=PasswordStatusResponse)
async def admin_get_user_password_status(
    username: str,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> PasswordStatusResponse:
    """
    Admin endpoint to check password status for any user.

    Requires admin privileges.
    """
    if not principal.is_admin:
        raise ForbiddenException("Only administrators can view other users' password status")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException(f"User '{username}' not found")

    from computor_types.password_utils import is_argon2_hash

    has_password = user.password is not None
    password_type = "none"

    if has_password:
        if is_argon2_hash(user.password):
            password_type = "argon2"
        else:
            password_type = "encrypted"  # Legacy

    return PasswordStatusResponse(
        user_id=str(user.id),
        username=user.username,
        has_password=has_password,
        password_reset_required=user.password_reset_required or False,
        password_type=password_type,
    )
