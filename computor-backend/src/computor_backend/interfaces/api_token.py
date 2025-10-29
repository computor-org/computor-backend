"""Backend ApiTokenInterface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.api_tokens import ApiTokenInterface as ApiTokenInterfaceBase, ApiTokenQuery
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.service import ApiToken


class ApiTokenInterface(ApiTokenInterfaceBase, BackendEntityInterface):
    """Backend-specific ApiTokenInterface with model and API configuration."""

    model = ApiToken
    endpoint = "api-tokens"
    cache_ttl = 60  # 1 minute - tokens can be created/revoked frequently

    @staticmethod
    def search(db: Session, query, params: Optional[ApiTokenQuery]):
        """
        Apply search filters to api_token query.

        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters

        Returns:
            Filtered query object
        """

        if params is None:
            return query

        # UUID filter
        if params.id is not None:
            query = query.filter(ApiToken.id == params.id)

        # User ID filter
        if params.user_id is not None:
            query = query.filter(ApiToken.user_id == params.user_id)

        # Revoked filter
        if params.revoked is not None:
            query = query.filter(ApiToken.revoked == params.revoked)

        # Active tokens only (not revoked and not expired)
        if hasattr(params, 'active') and params.active is not None:
            from datetime import datetime
            if params.active:
                query = query.filter(
                    ApiToken.revoked == False,
                    (ApiToken.expires_at == None) | (ApiToken.expires_at > datetime.utcnow())
                )

        return query
