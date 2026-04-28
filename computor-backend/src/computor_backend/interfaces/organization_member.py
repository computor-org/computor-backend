"""Backend OrganizationMemberInterface with SQLAlchemy model."""

from typing import Optional

from sqlalchemy.orm import Session

from computor_types.organization_members import (
    OrganizationMemberInterface as OrganizationMemberInterfaceBase,
    OrganizationMemberQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.organization import OrganizationMember
from computor_backend.permissions.handlers_impl import (
    make_scope_member_custom_permissions,
)


# UPDATE goes through ``custom_permissions`` instead of the generic
# ``build_query`` path, so we can inspect the *new* role being assigned
# in the payload — a ``_manager`` must not be able to PATCH a member
# to ``_owner``, even if they are otherwise allowed to edit the row.
custom_permissions_organization_member = make_scope_member_custom_permissions(
    OrganizationMember,
    scope="organization",
    scope_fk="organization_id",
    role_fk="organization_role_id",
)


class OrganizationMemberInterface(
    OrganizationMemberInterfaceBase, BackendEntityInterface
):
    """Backend-specific OrganizationMember interface."""

    model = OrganizationMember
    endpoint = "organization-members"
    cache_ttl = 300
    custom_permissions = custom_permissions_organization_member

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
