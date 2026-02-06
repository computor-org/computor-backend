"""
API Token repository for direct database access with optional caching.

This module provides the ApiTokenRepository class that handles
all database operations for ApiToken entities with transparent caching.

Note: Token validation caching is handled separately in api_token_cache.py
for performance-critical authentication flows. This repository is for
CRUD operations and administrative queries.
"""

from datetime import datetime, timezone
from typing import List, Optional, Set
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.service import ApiToken


class ApiTokenRepository(BaseRepository[ApiToken]):
    """
    Repository for ApiToken entity database operations with optional caching.

    Caching is automatic when cache instance is provided to constructor.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize API token repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, ApiToken, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "api_token"

    def get_ttl(self) -> int:
        """Tokens are validated frequently - use 2 minute TTL for CRUD cache."""
        return 120  # 2 minutes

    def get_entity_tags(self, entity: ApiToken) -> Set[str]:
        """
        Get cache tags for an API token.

        Tags:
        - api_token:{id} - The specific token
        - api_token:list - All token list queries
        - api_token:user:{user_id} - All tokens for a user
        - api_token:name:{user_id}:{name} - Token by name for user
        - api_token:hash:{hash_prefix} - Token by hash prefix (first 16 chars)
        """
        tags = {
            f"api_token:{entity.id}",
            "api_token:list",
        }

        if entity.user_id:
            tags.add(f"api_token:user:{entity.user_id}")

        if entity.name and entity.user_id:
            tags.add(f"api_token:name:{entity.user_id}:{entity.name}")

        if entity.token_hash:
            # Use hex prefix for tag (first 16 chars of hex)
            hash_prefix = entity.token_hash.hex()[:16]
            tags.add(f"api_token:hash:{hash_prefix}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"api_token:list"}

        if "user_id" in filters:
            tags.add(f"api_token:user:{filters['user_id']}")

        return tags

    # ========================================================================
    # Specialized queries (with caching if enabled)
    # ========================================================================

    def find_by_user(self, user_id: str, include_revoked: bool = False) -> List[ApiToken]:
        """
        Find all tokens for a user (cached if enabled).

        Args:
            user_id: User identifier
            include_revoked: Whether to include revoked tokens

        Returns:
            List of tokens for the user
        """
        if include_revoked:
            return self.find_by(user_id=user_id)

        # For active-only, use custom query
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"user_active:{user_id}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        entities = self.db.query(ApiToken).filter(
            ApiToken.user_id == user_id,
            ApiToken.revoked_at.is_(None)
        ).all()

        if self._use_cache():
            key = self.cache.key(self.entity_type, f"user_active:{user_id}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={f"api_token:user:{user_id}", "api_token:list"},
                ttl=self.get_ttl()
            )

        return entities

    def find_by_name(self, user_id: str, name: str) -> Optional[ApiToken]:
        """
        Find token by name for a user (cached if enabled).

        Args:
            user_id: User identifier
            name: Token name

        Returns:
            Token if found, None otherwise
        """
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"name:{user_id}:{name}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached)

        entity = self.db.query(ApiToken).filter(
            ApiToken.user_id == user_id,
            ApiToken.name == name
        ).first()

        if entity and self._use_cache():
            key = self.cache.key(self.entity_type, f"name:{user_id}:{name}")
            tags = self.get_entity_tags(entity)
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity),
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity

    def find_active_by_name(self, user_id: str, name: str) -> Optional[ApiToken]:
        """
        Find active (non-revoked) token by name for a user (cached if enabled).

        Args:
            user_id: User identifier
            name: Token name

        Returns:
            Active token if found, None otherwise
        """
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"active_name:{user_id}:{name}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached)

        entity = self.db.query(ApiToken).filter(
            ApiToken.user_id == user_id,
            ApiToken.name == name,
            ApiToken.revoked_at.is_(None)
        ).first()

        if entity and self._use_cache():
            key = self.cache.key(self.entity_type, f"active_name:{user_id}:{name}")
            tags = self.get_entity_tags(entity)
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity),
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity

    def find_all_active_by_name(self, user_id: str, name: str) -> List[ApiToken]:
        """
        Find all active (non-revoked) tokens with a given name for a user.

        Args:
            user_id: User identifier
            name: Token name

        Returns:
            List of active tokens with that name
        """
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"all_active_name:{user_id}:{name}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        entities = self.db.query(ApiToken).filter(
            ApiToken.user_id == user_id,
            ApiToken.name == name,
            ApiToken.revoked_at.is_(None)
        ).all()

        if self._use_cache():
            key = self.cache.key(self.entity_type, f"all_active_name:{user_id}:{name}")
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(
                key=key,
                payload=serialized,
                tags={f"api_token:user:{user_id}", f"api_token:name:{user_id}:{name}"},
                ttl=self.get_ttl()
            )

        return entities

    def find_by_token_hash(self, token_hash: bytes) -> Optional[ApiToken]:
        """
        Find token by hash (for authentication).

        Note: For high-performance auth validation, use api_token_cache.py instead.
        This method is for administrative lookups.

        Args:
            token_hash: The SHA-256 hash of the token

        Returns:
            Token if found, None otherwise
        """
        return self.db.query(ApiToken).filter(
            ApiToken.token_hash == token_hash
        ).first()

    def revoke(
        self,
        token_id: str,
        reason: Optional[str] = None,
        revoked_by: Optional[str] = None
    ) -> Optional[ApiToken]:
        """
        Revoke a token by ID.

        Args:
            token_id: Token ID to revoke
            reason: Optional revocation reason
            revoked_by: User ID who revoked the token

        Returns:
            Revoked token or None if not found
        """
        token = self.get_by_id_optional(token_id)
        if not token:
            return None

        if token.revoked_at:
            return token  # Already revoked

        token.revoked_at = datetime.now(timezone.utc)
        token.revocation_reason = reason
        if revoked_by:
            token.updated_by = revoked_by

        self.db.commit()
        self.db.refresh(token)

        # Invalidate caches
        if self._use_cache():
            tags = self.get_entity_tags(token)
            self.cache.invalidate_tags(*tags)

        return token

    def revoke_all_by_name(
        self,
        user_id: str,
        name: str,
        reason: Optional[str] = None
    ) -> int:
        """
        Revoke all active tokens with a given name for a user.

        Args:
            user_id: User identifier
            name: Token name to revoke
            reason: Optional revocation reason

        Returns:
            Number of tokens revoked
        """
        now = datetime.now(timezone.utc)

        tokens = self.db.query(ApiToken).filter(
            ApiToken.user_id == user_id,
            ApiToken.name == name,
            ApiToken.revoked_at.is_(None)
        ).all()

        for token in tokens:
            token.revoked_at = now
            token.revocation_reason = reason

        if tokens:
            self.db.flush()

            # Invalidate caches
            if self._use_cache():
                self.cache.invalidate_tags(
                    f"api_token:user:{user_id}",
                    f"api_token:name:{user_id}:{name}",
                    "api_token:list"
                )

        return len(tokens)

    def update_last_used(self, token_id: str) -> None:
        """
        Update the last_used_at timestamp and increment usage_count.

        Args:
            token_id: Token ID to update
        """
        self.db.query(ApiToken).filter(ApiToken.id == token_id).update({
            "last_used_at": datetime.now(timezone.utc),
            "usage_count": ApiToken.usage_count + 1
        })
        self.db.commit()
