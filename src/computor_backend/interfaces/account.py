"""Backend Account interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.accounts import (
    AccountInterface as AccountInterfaceBase,
    AccountQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.auth import Account


class AccountInterface(AccountInterfaceBase, BackendEntityInterface):
    """Backend-specific Account interface with model attached."""

    model = Account
    endpoint = "accounts"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[AccountQuery]):
        """
        Apply search filters to account query.
        
        Note: Implement specific filters based on query parameters.
        This is a placeholder - update with actual filter logic.
        """
        # TODO: Implement search filters based on AccountQuery fields
        return query
