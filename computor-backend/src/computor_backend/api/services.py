"""
Service API endpoints.

Provides endpoints for service account management and self-identification.
"""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session, joinedload

from computor_backend.database import get_db
from computor_backend.exceptions import ForbiddenException, NotFoundException, UserNotFoundException
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.model.auth import User
from computor_backend.model.service import Service
from computor_backend.business_logic.service_accounts import (
    create_service_account,
    get_service_account,
    list_service_accounts,
    update_service_account,
    update_service_heartbeat,
    delete_service_account,
)
from computor_types.services import (
    ServiceCreate,
    ServiceGet,
    ServiceUpdate,
    ServiceQuery,
)


services_router = APIRouter()


# =============================================================================
# Self-identification endpoint (must be before /{service_id} routes)
# =============================================================================

@services_router.get("/me", response_model=ServiceGet)
async def get_service_me(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """
    Get the authenticated service account's configuration.

    This endpoint is designed for Temporal workers and other services
    to fetch their configuration on startup using their API token.

    Requires authentication with a service account (is_service=true).

    Returns:
        ServiceGet: The service's configuration including config dict, service_type_path, etc.

    Raises:
        403: If the authenticated user is not a service account
        404: If the service record is not found for the user
    """
    user_id = principal.get_user_id_or_throw()

    # Get the user and check if it's a service account
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundException(
            error_code="NF_002",
            detail=f"User {user_id} not found"
        )

    if not user.is_service:
        raise ForbiddenException(
            error_code="AUTHZ_010",
            detail="This endpoint is only available for service accounts",
            context={"user_id": str(user_id)}
        )

    # Get the associated service with its service type
    service = (
        db.query(Service)
        .options(joinedload(Service.service_type))
        .filter(Service.user_id == user_id)
        .first()
    )

    if not service:
        raise NotFoundException(
            error_code="NF_010",
            detail="Service record not found for this service account",
            context={"user_id": str(user_id)}
        )

    # Get service type path if available
    service_type_path = None
    if service.service_type:
        service_type_path = str(service.service_type.path)

    return ServiceGet(
        id=str(service.id),
        slug=service.slug,
        name=service.name,
        description=service.description,
        service_type_id=str(service.service_type_id) if service.service_type_id else None,
        service_type_path=service_type_path,
        user_id=str(service.user_id),
        config=service.config or {},
        enabled=service.enabled,
        last_seen_at=service.last_seen_at,
        properties=service.properties
    )


# =============================================================================
# CRUD endpoints for service account management
# =============================================================================

@services_router.post("", response_model=ServiceGet, status_code=status.HTTP_201_CREATED)
def create_service_endpoint(
    service_data: ServiceCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Create a new service account."""
    return create_service_account(service_data, permissions, db)


@services_router.get("", response_model=List[ServiceGet])
def list_services_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    query: ServiceQuery = Depends(),
    db: Session = Depends(get_db),
):
    """List all service accounts with optional filtering."""
    return list_service_accounts(permissions, db, query)


@services_router.get("/{service_id}", response_model=ServiceGet)
def get_service_endpoint(
    service_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get service account details by ID."""
    return get_service_account(service_id, permissions, db)


@services_router.patch("/{service_id}", response_model=ServiceGet)
def update_service_endpoint(
    service_id: UUID | str,
    service_data: ServiceUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Update service account details."""
    return update_service_account(service_id, service_data, permissions, db)


@services_router.put("/{service_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def service_heartbeat_endpoint(
    service_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Update service last_seen_at timestamp (heartbeat)."""
    update_service_heartbeat(service_id, permissions, db)


@services_router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_endpoint(
    service_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Delete (archive) a service account."""
    delete_service_account(service_id, permissions, db)
