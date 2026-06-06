"""Git server registry endpoints (admin / _organization_manager).

The registry holds the git server instances Computor knows about and (for
managed instances) their encrypted service tokens. Tokens are write-only.
"""
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from computor_backend.business_logic.git_registry import (
    create_git_server,
    delete_git_server,
    get_git_server,
    list_git_servers,
    update_git_server,
)
from computor_backend.database import get_db
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_types.git_registry import GitServerCreate, GitServerGet, GitServerUpdate

git_servers_router = APIRouter(prefix="/git-servers")


@git_servers_router.post("", response_model=GitServerGet, status_code=status.HTTP_201_CREATED)
def create_git_server_endpoint(
    data: GitServerCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Register a git server instance (the service token is stored encrypted)."""
    return create_git_server(data, permissions, db)


@git_servers_router.get("", response_model=List[GitServerGet])
def list_git_servers_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    return list_git_servers(permissions, db)


@git_servers_router.get("/{server_id}", response_model=GitServerGet)
def get_git_server_endpoint(
    server_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    return get_git_server(server_id, permissions, db)


@git_servers_router.patch("/{server_id}", response_model=GitServerGet)
def update_git_server_endpoint(
    server_id: UUID,
    data: GitServerUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    return update_git_server(server_id, data, permissions, db)


@git_servers_router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_git_server_endpoint(
    server_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    delete_git_server(server_id, permissions, db)
