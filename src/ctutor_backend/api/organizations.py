from typing import Annotated
from uuid import UUID
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.principal import Principal

from ctutor_backend.database import get_db
from ctutor_backend.interface.organizations import OrganizationInterface
from ctutor_backend.api.api_builder import CrudRouter

# Import business logic
from ctutor_backend.business_logic.organizations import update_organization_token

organization_router = CrudRouter(OrganizationInterface)

class OrganizationUpdateTokenQuery(BaseModel):
    type: str

class OrganizationUpdateTokenUpdate(BaseModel):
    token: str

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