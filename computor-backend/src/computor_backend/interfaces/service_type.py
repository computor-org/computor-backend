"""Backend ServiceTypeInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.service_type import ServiceTypeInterface as ServiceTypeInterfaceBase, ServiceTypeQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.service import ServiceType
from computor_backend.custom_types import Ltree


class ServiceTypeInterface(ServiceTypeInterfaceBase, BackendEntityInterface):
    """Backend-specific ServiceTypeInterface with model and API configuration."""

    model = ServiceType
    endpoint = "service-types"
    cache_ttl = 600  # 10 minutes - service types don't change frequently

    @staticmethod
    def search(db: Session, query, params: Optional[ServiceTypeQuery]):
        """
        Apply search filters to service_type query.

        Supports hierarchical path queries using Ltree operators:
        - path: Exact match
        - path_descendant: All descendants of a path (e.g., 'testing' returns testing.*)
        - path_pattern: Ltree lquery pattern matching

        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters

        Returns:
            Filtered query object
        """

        if params is None:
            return query

        # UUID filter
        if params.id is not None:
            query = query.filter(ServiceType.id == params.id)

        # Exact path match
        if params.path is not None:
            query = query.filter(ServiceType.path == Ltree(params.path))

        # Hierarchical descendant query (e.g., 'testing' returns all testing.*)
        if params.path_descendant is not None:
            # Use Ltree descendant-of operator (<@)
            query = query.filter(ServiceType.path.descendant_of(Ltree(params.path_descendant)))

        # Pattern matching (ltree lquery)
        if params.path_pattern is not None:
            # Use Ltree pattern matching operator (~)
            query = query.filter(ServiceType.path.op('~')(params.path_pattern))

        # Category filter
        if params.category is not None:
            query = query.filter(ServiceType.category == params.category)

        # Enabled filter
        if params.enabled is not None:
            query = query.filter(ServiceType.enabled == params.enabled)

        # Plugin module filter
        if params.plugin_module is not None:
            query = query.filter(ServiceType.plugin_module == params.plugin_module)

        return query
