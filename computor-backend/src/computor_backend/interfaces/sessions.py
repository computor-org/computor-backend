"""Backend SessionInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.sessions import SessionInterface as SessionInterfaceBase, SessionQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.auth import Session as SessionModel

class SessionInterface(SessionInterfaceBase, BackendEntityInterface):
    """Backend-specific SessionInterface with model and API configuration."""
    
    model = SessionModel
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
        
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(SessionModel.id == params.id)
        if params.user_id is not None:
            query = query.filter(SessionModel.user_id == params.user_id)

        return query
