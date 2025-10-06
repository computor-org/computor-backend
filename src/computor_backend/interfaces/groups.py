"""Backend GroupInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.groups import GroupInterface as GroupInterfaceBase, GroupQuery
from computor_backend.interfaces.base import BackendEntityInterface
# TODO: Import actual model when available
# from computor_backend.model import Group

class GroupInterface(GroupInterfaceBase, BackendEntityInterface):
    """Backend-specific GroupInterface with model and API configuration."""
    
    # model = Group  # TODO: Set when model is available
    endpoint = "groups"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[GroupQuery]):
        """
        Apply search filters to group query.
        
        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters
            
        Returns:
            Filtered query object
        """
        # TODO: Implement search logic when model is available
        return query
