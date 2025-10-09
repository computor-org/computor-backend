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
            query = query.filter(Account.id == params.id)
        if params.provider is not None:
            query = query.filter(Account.provider == params.provider)
        if params.type is not None:
            query = query.filter(Account.type == params.type)
        if params.provider_account_id is not None:
            query = query.filter(Account.provider_account_id == params.provider_account_id)
        if params.user_id is not None:
            query = query.filter(Account.user_id == params.user_id)

        return query
