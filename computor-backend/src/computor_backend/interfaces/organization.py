"""Backend Organization interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.organizations import (
    OrganizationInterface as OrganizationInterfaceBase,
    OrganizationQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.organization import Organization


class OrganizationInterface(OrganizationInterfaceBase, BackendEntityInterface):
    """Backend-specific Organization interface with model attached."""

    model = Organization
    endpoint = "organizations"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[OrganizationQuery]):
        """Apply search filters to organization query."""
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Organization.id == params.id)
        if params.number is not None:
            query = query.filter(Organization.number == params.number)
        if params.title is not None:
            query = query.filter(Organization.title == params.title)
        if params.description is not None:
            query = query.filter(Organization.description.ilike(f"%{params.description}%"))
        if params.email is not None:
            query = query.filter(Organization.email == params.email)
        if params.organization_type is not None:
            query = query.filter(Organization.organization_type == params.organization_type)
        if params.user_id is not None:
            query = query.filter(Organization.user_id == params.user_id)
        if params.path is not None:
            query = query.filter(Organization.path == params.path)

        return query
