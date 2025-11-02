"""Backend ServiceInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.services import ServiceInterface as ServiceInterfaceBase, ServiceQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.service import Service


class ServiceInterface(ServiceInterfaceBase, BackendEntityInterface):
    """Backend-specific ServiceInterface with model and API configuration."""

    model = Service
    endpoint = "service-accounts"
    cache_ttl = 300  # 5 minutes

    @staticmethod
    def search(db: Session, query, params: Optional[ServiceQuery]):
        """
        Apply search filters to service query.

        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters

        Returns:
            Filtered query object
        """

        if params is None:
            return query

        # ID filter
        if params.id is not None:
            query = query.filter(Service.id == params.id)

        # Slug filter
        if params.slug is not None:
            query = query.filter(Service.slug == params.slug)

        # ServiceType ID filter
        if params.service_type_id is not None:
            query = query.filter(Service.service_type_id == params.service_type_id)

        # Enabled filter
        if params.enabled is not None:
            query = query.filter(Service.enabled == params.enabled)

        # User ID filter (service owner)
        if params.user_id is not None:
            query = query.filter(Service.user_id == params.user_id)

        return query
