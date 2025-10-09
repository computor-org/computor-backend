"""Backend ExecutionBackendInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.execution_backends import ExecutionBackendInterface as ExecutionBackendInterfaceBase, ExecutionBackendQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.execution import ExecutionBackend

class ExecutionBackendInterface(ExecutionBackendInterfaceBase, BackendEntityInterface):
    """Backend-specific ExecutionBackendInterface with model and API configuration."""
    
    model = ExecutionBackend
    endpoint = "execution-backends"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[ExecutionBackendQuery]):
        """
        Apply search filters to executionbackend query.
        
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
            query = query.filter(ExecutionBackend.id == params.id)
        if params.type is not None:
            query = query.filter(ExecutionBackend.type == params.type)
        if params.slug is not None:
            query = query.filter(ExecutionBackend.slug == params.slug)

        return query
