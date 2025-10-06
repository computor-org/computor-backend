"""Backend Extension interface with SQLAlchemy model."""

from typing import Optional, Any
from sqlalchemy.orm import Session

from computor_types.extensions import ExtensionInterface as ExtensionInterfaceBase
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.extension import Extension


class ExtensionInterface(ExtensionInterfaceBase, BackendEntityInterface):
    """Backend-specific Extension interface with model and API configuration."""

    model = Extension
    endpoint = "extensions"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[Any] = None):
        """Apply search filters to extension query."""
        if params is None:
            return query

        if hasattr(params, 'id') and params.id is not None:
            query = query.filter(Extension.id == params.id)
        if hasattr(params, 'name') and params.name is not None:
            query = query.filter(Extension.name == params.name)
        if hasattr(params, 'archived') and params.archived is not None:
            if params.archived:
                query = query.filter(Extension.archived_at.isnot(None))
            else:
                query = query.filter(Extension.archived_at.is_(None))

        return query
