"""Backend OrganizationRoleInterface with SQLAlchemy model."""

from typing import Optional

from sqlalchemy.orm import Session

from computor_types.organization_roles import (
    OrganizationRoleInterface as OrganizationRoleInterfaceBase,
    OrganizationRoleQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.organization import OrganizationRole


class OrganizationRoleInterface(
    OrganizationRoleInterfaceBase, BackendEntityInterface
):
    """Backend-specific OrganizationRoleInterface with model and routing."""

    model = OrganizationRole
    endpoint = "organization-roles"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[OrganizationRoleQuery]):
        if params is None:
            return query
        if params.id is not None:
            query = query.filter(OrganizationRole.id == params.id)
        if params.title is not None:
            query = query.filter(OrganizationRole.title == params.title)
        if params.builtin is not None:
            query = query.filter(OrganizationRole.builtin == params.builtin)
        return query
