"""Backend SessionInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.sessions import SessionInterface as SessionInterfaceBase, SessionQuery
from computor_backend.interfaces.base import BackendEntityInterface
# TODO: Import actual model when available
# from computor_backend.model import Session

class SessionInterface(SessionInterfaceBase, BackendEntityInterface):
    """Backend-specific SessionInterface with model and API configuration."""
    
    # model = Session  # TODO: Set when model is available
    endpoint = "sessions"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[SessionQuery]):
        """
        Apply search filters to session query.
        
        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters
            
        Returns:
            Filtered query object
        """
        # TODO: Implement search logic when model is available
        return query
