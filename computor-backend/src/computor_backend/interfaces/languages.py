"""Backend LanguageInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.languages import LanguageInterface as LanguageInterfaceBase, LanguageQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.language import Language

class LanguageInterface(LanguageInterfaceBase, BackendEntityInterface):
    """Backend-specific LanguageInterface with model and API configuration."""
    
    model = Language
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
        
        if params is None:
            return query

        if params.code is not None:
            query = query.filter(Language.code == params.code)
        if params.name is not None:
            query = query.filter(Language.name == params.name)
        if params.native_name is not None:
            query = query.filter(Language.native_name == params.native_name)

        return query
