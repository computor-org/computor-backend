"""Backend GroupInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.groups import GroupInterface as GroupInterfaceBase, GroupQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.group import Group

class GroupInterface(GroupInterfaceBase, BackendEntityInterface):
    """Backend-specific GroupInterface with model and API configuration."""
    
    model = Group
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
        
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Group.id == params.id)
        if params.title is not None:
            query = query.filter(Group.title == params.title)

        return query
