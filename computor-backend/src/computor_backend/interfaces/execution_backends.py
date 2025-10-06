"""Backend ExecutionBackendInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.execution_backends import ExecutionBackendInterface as ExecutionBackendInterfaceBase, ExecutionBackendQuery
from computor_backend.interfaces.base import BackendEntityInterface
# TODO: Import actual model when available
# from computor_backend.model import ExecutionBackend

class ExecutionBackendInterface(ExecutionBackendInterfaceBase, BackendEntityInterface):
    """Backend-specific ExecutionBackendInterface with model and API configuration."""
    
    # model = ExecutionBackend  # TODO: Set when model is available
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
        # TODO: Implement search logic when model is available
        return query
