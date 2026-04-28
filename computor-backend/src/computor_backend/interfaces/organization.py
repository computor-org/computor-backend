"""Backend Organization interface with SQLAlchemy model."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from computor_types.organizations import (
    OrganizationInterface as OrganizationInterfaceBase,
    OrganizationQuery,
)
from computor_types.custom_types import Ltree
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.organization import (
    Organization,
    OrganizationMember,
)

logger = logging.getLogger(__name__)


async def post_create_organization(organization, db: Session):
    """Auto-grant the creating user ``_owner`` on the new organization.

    Without this, a non-admin user who has the global
    ``organization:create`` permission could create an organization but
    would have no scoped role on it afterwards — locking themselves out
    of editing it. Admins skip this (they already bypass scope checks).
    """
    if organization is None or organization.created_by is None:
        return
    try:
        existing = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.user_id == organization.created_by,
                OrganizationMember.organization_id == organization.id,
            )
            .first()
        )
        if existing is not None:
            return

        member = OrganizationMember(
            user_id=organization.created_by,
            organization_id=organization.id,
            organization_role_id="_owner",
            created_by=organization.created_by,
            updated_by=organization.created_by,
        )
        db.add(member)
        db.flush()
        logger.info(
            "Auto-assigned creator %s as _owner of organization %s",
            organization.created_by,
            organization.id,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to auto-assign creator as _owner for organization %s",
            getattr(organization, "id", None),
        )


class OrganizationInterface(OrganizationInterfaceBase, BackendEntityInterface):
    """Backend-specific Organization interface with model attached."""

    model = Organization
    endpoint = "organizations"
    cache_ttl = 600
    post_create = post_create_organization

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
            # Convert string to Ltree for proper comparison
            query = query.filter(Organization.path == Ltree(params.path))

        return query
