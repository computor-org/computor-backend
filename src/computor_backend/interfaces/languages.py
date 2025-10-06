"""Backend LanguageInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.languages import LanguageInterface as LanguageInterfaceBase, LanguageQuery
from computor_backend.interfaces.base import BackendEntityInterface
# TODO: Import actual model when available
# from computor_backend.model import Language

class LanguageInterface(LanguageInterfaceBase, BackendEntityInterface):
    """Backend-specific LanguageInterface with model and API configuration."""
    
    # model = Language  # TODO: Set when model is available
    endpoint = "languages"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[LanguageQuery]):
        """
        Apply search filters to language query.
        
        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters
            
        Returns:
            Filtered query object
        """
        # TODO: Implement search logic when model is available
        return query
