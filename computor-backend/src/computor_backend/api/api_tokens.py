"""API token management endpoints."""
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.business_logic.api_tokens import (
    create_api_token,
    create_api_token_admin,
    get_api_token,
    list_api_tokens,
    revoke_api_token,
    update_api_token_admin,
)
from computor_types.api_tokens import (
    ApiTokenCreate,
    ApiTokenAdminCreate,
    ApiTokenCreateResponse,
    ApiTokenGet,
    ApiTokenUpdate,
)

api_tokens_router = APIRouter()


@api_tokens_router.post("", response_model=ApiTokenCreateResponse, status_code=status.HTTP_201_CREATED)
def create_token_endpoint(
    token_data: ApiTokenCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """
    Create a new API token.

    Returns the full token string (only shown once - cannot be retrieved later).
    """
    return create_api_token(token_data, permissions, db)


@api_tokens_router.post("/admin/create", response_model=ApiTokenCreateResponse, status_code=status.HTTP_201_CREATED)
def create_token_admin_endpoint(
    token_data: ApiTokenAdminCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """
    Create an API token with a predefined value (admin-only).

    This endpoint is for initial deployment where tokens need to be known in advance.
    Requires admin permissions. Regular users should use the standard token creation endpoint.
    """
    return create_api_token_admin(token_data, permissions, db)


@api_tokens_router.patch("/admin/{token_id}", response_model=ApiTokenGet)
def update_token_admin_endpoint(
    token_id: UUID,
    token_data: ApiTokenUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """
    Update an API token (admin-only).

    This endpoint is primarily for updating token scopes after course creation during deployment.
    Requires admin permissions.
    """
    return update_api_token_admin(token_id, token_data, permissions, db)


@api_tokens_router.get("", response_model=List[ApiTokenGet])
def list_tokens_endpoint(
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    include_revoked: bool = Query(False, description="Include revoked tokens"),
    permissions: Annotated[Principal, Depends(get_current_principal)] = None,
    db: Session = Depends(get_db),
):
    """
    List API tokens.

    Admins can list all tokens or filter by user_id.
    Regular users can only list their own tokens.
    """
    return list_api_tokens(user_id, include_revoked, permissions, db)


@api_tokens_router.get("/{token_id}", response_model=ApiTokenGet)
def get_token_endpoint(
    token_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get API token details by ID (does not include the actual token)."""
    return get_api_token(token_id, permissions, db)


@api_tokens_router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token_endpoint(
    token_id: UUID,
    reason: Optional[str] = Query(None, description="Revocation reason"),
    permissions: Annotated[Principal, Depends(get_current_principal)] = None,
    db: Session = Depends(get_db),
):
    """
    Revoke an API token.

    The token will be immediately invalidated and cannot be used for authentication.
    """
    revoke_api_token(token_id, reason, permissions, db)
