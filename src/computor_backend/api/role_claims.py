from typing import Annotated
from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session

from computor_backend.permissions.principal import Principal
from computor_backend.permissions.auth import get_current_principal
from computor_backend.database import get_db
from computor_types.roles_claims import RoleClaimList, RoleClaimQuery

# Import business logic
from computor_backend.business_logic.role_claims import list_role_claims

role_claim_router = APIRouter()


@role_claim_router.get("", response_model=list[RoleClaimList])
async def list_role_claim(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    role_claim_query: RoleClaimQuery = Depends(),
    db: Session = Depends(get_db)
):
    """List role claims."""
    return list_role_claims(permissions, role_claim_query, db)
