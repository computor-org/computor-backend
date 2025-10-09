"""Backend Role interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.roles import (
    RoleInterface as RoleInterfaceBase,
    RoleQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.role import Role


class RoleInterface(RoleInterfaceBase, BackendEntityInterface):
    """Backend-specific Role interface with model attached."""

    model = Role
    endpoint = "roles"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[RoleQuery]):
        """Apply search filters to role query."""
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Role.id == params.id)
        if params.title is not None:
            query = query.filter(Role.title == params.title)
        if params.description is not None:
            query = query.filter(Role.description.ilike(f"%{params.description}%"))
        if params.builtin is not None:
            query = query.filter(Role.builtin == params.builtin)

        return query
