from typing import Annotated
from uuid import UUID
from fastapi import Depends, Query
from sqlalchemy.orm import Session
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal

from computor_backend.database import get_db
from computor_backend.api.api_builder import CrudRouter
from computor_backend.api.exceptions import ForbiddenException, NotFoundException

# Import business logic
from computor_backend.business_logic.organizations import update_organization_token
from computor_backend.business_logic.cascade_deletion import delete_organization_cascade
from computor_backend.interfaces import OrganizationInterface
from computor_backend.model import Organization
from computor_backend.services.storage_service import get_storage_service

# Import DTOs from computor_types
from computor_types.organizations import (
    OrganizationUpdateTokenQuery,
    OrganizationUpdateTokenUpdate,
)
from computor_types.cascade_deletion import CascadeDeleteResult

organization_router = CrudRouter(OrganizationInterface)

@organization_router.router.patch("/{organization_id}/token", status_code=201)
def patch_organizations_token(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    organization_id: UUID | str,
    payload: OrganizationUpdateTokenUpdate,
    params: OrganizationUpdateTokenQuery = Depends(),
    db: Session = Depends(get_db)
):
    """Update organization provider token."""
    update_organization_token(
        organization_id=organization_id,
        token_type=params.type,
        token=payload.token,
        permissions=permissions,
        db=db,
    )


@organization_router.router.delete(
    "/{organization_id}",
    response_model=CascadeDeleteResult,
    summary="Delete organization and all descendant data",
    description="""
    Delete an organization and ALL its descendant data including:
    - All course families and their courses
    - All course members, groups, contents, submissions
    - All example repositories and examples
    - All student profiles (NOT the users themselves)
    - All messages targeted to the organization

    **WARNING**: This is a destructive operation. Use dry_run=true to preview.

    Users and accounts are NOT deleted - only organization-specific data.
    """
)
async def delete_organization_endpoint(
    organization_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    dry_run: bool = Query(
        default=False,
        description="If true, only returns preview without deleting"
    ),
) -> CascadeDeleteResult:
    """Delete organization and all descendant data."""
    if not permissions.is_admin:
        raise ForbiddenException("Deletion requires admin permissions")

    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == str(organization_id)).first()
    if not org:
        raise NotFoundException(f"Organization not found: {organization_id}")

    storage = get_storage_service()
    result = await delete_organization_cascade(
        db=db,
        organization_id=str(organization_id),
        storage=storage,
        dry_run=dry_run
    )

    return result