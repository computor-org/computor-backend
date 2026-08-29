from types import SimpleNamespace
from typing import Annotated
from uuid import UUID
from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.core import can_perform_action
from computor_backend.permissions.principal import Principal

from computor_backend.database import get_db
from computor_backend.api.api_builder import CrudRouter, invalidate_request_principal
from computor_backend.exceptions import ConflictException, ForbiddenException, NotFoundException

# Import business logic
from computor_backend.business_logic.organizations import update_organization_token
from computor_backend.business_logic.cascade_deletion import delete_organization_cascade
from computor_backend.interfaces import OrganizationInterface
from computor_backend.model import CourseFamily, Organization
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
    request: Request,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    dry_run: bool = Query(
        default=False,
        description="If true, only returns preview without deleting"
    ),
) -> CascadeDeleteResult:
    """Delete organization — owners and admins only, and only when it has no course families left."""
    oid = str(organization_id)
    # Through the entity's permission handler (``delete`` -> scope ``_owner``):
    # the same answer the generic route would give. ``_organization_manager``
    # is a manager, not an owner, and deliberately does not pass.
    if not can_perform_action(permissions, Organization, "delete", resource_id=oid):
        raise ForbiddenException(
            detail="Only an owner of this organization (or an administrator) can delete it."
        )

    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == oid).first()
    if not org:
        raise NotFoundException(detail=f"Organization not found: {organization_id}")

    # Guard: never cascade through course families (and their courses / Forgejo
    # repos / members). The organization must be emptied top-down first.
    family_count = db.query(CourseFamily).filter(CourseFamily.organization_id == oid).count()
    blocked_reason = None
    if family_count > 0:
        blocked_reason = (
            f"This organization still has {family_count} course "
            f"{'families' if family_count != 1 else 'family'}. Delete "
            f"{'them' if family_count != 1 else 'it'} first (and their courses), then delete the organization."
        )
    if blocked_reason and not dry_run:
        raise ConflictException(detail=blocked_reason)

    storage = get_storage_service()
    result = await delete_organization_cascade(
        db=db,
        organization_id=oid,
        storage=storage,
        dry_run=dry_run
    )
    if dry_run:
        # Tell the client up front what the real call would refuse.
        result.blocked_reason = blocked_reason
        return result

    if not result.errors:
        # The org's scope members went with the row; drop the view caches
        # keyed on it and the caller's own cached roles (they just lost one).
        organization_router._invalidate_caches_for(
            SimpleNamespace(id=oid, organization_id=oid)
        )
        await invalidate_request_principal(request, what="deleting an organization")

    return result