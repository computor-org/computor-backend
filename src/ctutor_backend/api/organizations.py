from typing import Annotated
from uuid import UUID
from fastapi import Depends
from gitlab import Gitlab
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.core import check_permissions
from ctutor_backend.permissions.principal import Principal

from ctutor_backend.api.exceptions import BadRequestException, NotImplementedException
from ctutor_backend.database import get_db
from ctutor_backend.interface.organizations import OrganizationInterface, OrganizationProperties
from ctutor_backend.api.api_builder import CrudRouter
from ctutor_backend.interface.tokens import encrypt_api_key
from ctutor_backend.model.organization import Organization

organization_router = CrudRouter(OrganizationInterface)

class OrganizationUpdateTokenQuery(BaseModel):
    type: str

class OrganizationUpdateTokenUpdate(BaseModel):
    token: str

@organization_router.router.patch("/{organization_id}/token", status_code=201)
def patch_organizations_token(permissions: Annotated[Principal, Depends(get_current_principal)], organization_id: UUID | str, payload: OrganizationUpdateTokenUpdate, params: OrganizationUpdateTokenQuery = Depends(),db: Session = Depends(get_db)):

    query = check_permissions(permissions,Organization,"update",db)

    try:
        organization = query.filter(Organization.id == organization_id).first()

        if params.type == "gitlab":

            gitlab = Gitlab(url=organization.properties["gitlab"]["url"],private_token=payload.token)

            groups = list(filter(lambda g  : g.full_path == organization.properties["gitlab"]["full_path"],
                       gitlab.groups.list(search=organization.properties["gitlab"]["full_path"],min_access_level=50)))

            if len(groups) == 0:
                raise BadRequestException()
            
            organization_properties = OrganizationProperties(**organization.properties)
            organization_properties.gitlab.token = encrypt_api_key(payload.token)
            organization.properties = organization_properties.model_dump()

            db.commit()
            db.refresh(organization)
        else:
            raise NotImplementedException()

    except:
        raise BadRequestException()