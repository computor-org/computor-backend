from typing import Annotated
from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session

from ctutor_backend.permissions.principal import Principal
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.database import get_db
from ctutor_backend.interface.roles_claims import RoleClaimList, RoleClaimQuery

# Import business logic
from ctutor_backend.business_logic.role_claims import list_role_claims

role_claim_router = APIRouter()


@role_claim_router.get("", response_model=list[RoleClaimList])
async def list_role_claim(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    role_claim_query: RoleClaimQuery = Depends(),
    db: Session = Depends(get_db)
):
    """List role claims."""
    return list_role_claims(permissions, role_claim_query, db)
