"""Backend Extension interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel

from computor_types.extensions import ExtensionInterface as ExtensionInterfaceBase
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.extension import Extension


class ExtensionQuery(BaseModel):
    """Query parameters for extensions."""
    id: Optional[str] = None
    publisher: Optional[str] = None
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None


class ExtensionInterface(ExtensionInterfaceBase, BackendEntityInterface):
    """Backend-specific Extension interface with model and API configuration."""

    model = Extension
    endpoint = "extensions"
    cache_ttl = 300
    query = ExtensionQuery

    @staticmethod
    def search(db: Session, query, params: Optional[ExtensionQuery] = None):
        """Apply search filters to extension query.

        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters

        Returns:
            Filtered query object
        """
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Extension.id == params.id)
        if params.publisher is not None:
            query = query.filter(Extension.publisher == params.publisher)
        if params.name is not None:
            query = query.filter(Extension.name == params.name)
        if params.display_name is not None:
            query = query.filter(Extension.display_name == params.display_name)
        if params.description is not None:
            query = query.filter(Extension.description.ilike(f"%{params.description}%"))

        return query
