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
        if params.id is not None:
            query = query.filter(Organization.id == params.id)
        if params.title is not None:
            query = query.filter(Organization.title == params.title)
        if params.abbreviation is not None:
            query = query.filter(Organization.abbreviation == params.abbreviation)
        if params.archived is not None and params.archived:
            query = query.filter(Organization.archived_at.isnot(None))
        else:
            query = query.filter(Organization.archived_at.is_(None))

        return query
