"""Backend OrganizationMemberInterface with SQLAlchemy model."""

from typing import Optional

from sqlalchemy.orm import Session

from computor_types.organization_members import (
    OrganizationMemberInterface as OrganizationMemberInterfaceBase,
    OrganizationMemberQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.organization import OrganizationMember


class OrganizationMemberInterface(
    OrganizationMemberInterfaceBase, BackendEntityInterface
):
    """Backend-specific OrganizationMember interface."""

    model = OrganizationMember
    endpoint = "organization-members"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[OrganizationMemberQuery]):
        if params is None:
            return query
        if params.id is not None:
            query = query.filter(OrganizationMember.id == params.id)
        if params.user_id is not None:
            query = query.filter(OrganizationMember.user_id == params.user_id)
        if params.organization_id is not None:
            query = query.filter(
                OrganizationMember.organization_id == params.organization_id
            )
        if params.organization_role_id is not None:
            query = query.filter(
                OrganizationMember.organization_role_id == params.organization_role_id
            )
        return query
