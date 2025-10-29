"""Service account management API endpoints."""
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
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
    ServiceList,
    ServiceUpdate,
    ServiceQuery,
)

service_accounts_router = APIRouter()


@service_accounts_router.post("", response_model=ServiceGet, status_code=status.HTTP_201_CREATED)
def create_service_endpoint(
    service_data: ServiceCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Create a new service account."""
    return create_service_account(service_data, permissions, db)


@service_accounts_router.get("", response_model=List[ServiceGet])
def list_services_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    query: ServiceQuery = Depends(),
    db: Session = Depends(get_db),
):
    """List all service accounts with optional filtering."""
    return list_service_accounts(permissions, db, query)


@service_accounts_router.get("/{service_id}", response_model=ServiceGet)
def get_service_endpoint(
    service_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get service account details by ID."""
    return get_service_account(service_id, permissions, db)


@service_accounts_router.patch("/{service_id}", response_model=ServiceGet)
def update_service_endpoint(
    service_id: UUID,
    service_data: ServiceUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Update service account details."""
    return update_service_account(service_id, service_data, permissions, db)


@service_accounts_router.put("/{service_id}/heartbeat", status_code=status.HTTP_204_NO_CONTENT)
def service_heartbeat_endpoint(
    service_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Update service last_seen_at timestamp (heartbeat)."""
    update_service_heartbeat(service_id, permissions, db)


@service_accounts_router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_endpoint(
    service_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Delete (archive) a service account."""
    delete_service_account(service_id, permissions, db)
