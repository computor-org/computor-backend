"""
Base class for view repositories.

View repositories handle complex aggregated queries that don't map to single entities.
Unlike entity repositories that inherit from BaseRepository[T], view repositories
work with query results, DTOs, and complex data structures.
"""

from abc import ABC
from typing import Any, Optional, Dict, List
from sqlalchemy.orm import Session
import logging

from ..cache import Cache

logger = logging.getLogger(__name__)


class ViewRepository(ABC):
    """
    Base class for view repositories that handle complex queries.

    Unlike entity repositories which work with single entity types,
    view repositories work with aggregated data, joins, and complex
    query results that get mapped to DTOs.

    View repositories provide:
    - User-specific view caching
    - Permission-aware queries
    - DTO mapping and serialization
    - Tag-based cache invalidation
    """

    def __init__(self, db: Session, cache: Optional[Cache] = None):
        """
        Initialize view repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables caching)
        """
        self.db = db
        self.cache = cache

    def _use_cache(self) -> bool:
        """Check if caching is enabled."""
        return self.cache is not None

    def _build_cache_key(self, user_id: str, view_type: str, view_id: Optional[str] = None, **kwargs) -> str:
        """
        Build a cache key for user views.

        Args:
            user_id: User ID
            view_type: Type of view (e.g., "courses", "course_content")
            view_id: Optional specific ID
            **kwargs: Additional parameters for cache key (e.g., params hash)

        Returns:
            Cache key string
        """
        if view_id:
            return f"user:{user_id}:{view_type}:{view_id}"
        elif kwargs:
            suffix = ":".join(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            return f"user:{user_id}:{view_type}:{suffix}"
        else:
            return f"user:{user_id}:{view_type}"

    def _get_cached_view(
        self,
        user_id: str,
        view_type: str,
        view_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get cached view data.

        Args:
            user_id: User ID
            view_type: View type
            view_id: Optional view ID

        Returns:
            Cached data or None
        """
        if not self._use_cache():
            return None

        cached = self.cache.get_user_view(
            user_id=str(user_id),
            view_type=view_type,
            view_id=str(view_id) if view_id else None
        )

        if cached is not None:
            logger.debug(f"Cache HIT: user={user_id}, view={view_type}, id={view_id}")
        else:
            logger.debug(f"Cache MISS: user={user_id}, view={view_type}, id={view_id}")

        return cached

    def _set_cached_view(
        self,
        user_id: str,
        view_type: str,
        data: Any,
        view_id: Optional[str] = None,
        ttl: Optional[int] = None,
        related_ids: Optional[Dict[str, str]] = None
    ):
        """
        Cache view data.

        Args:
            user_id: User ID
            view_type: View type
            data: Data to cache
            view_id: Optional view ID
            ttl: Time-to-live in seconds
            related_ids: Related entity IDs for tag generation
        """
        if not self._use_cache():
            return

        self.cache.set_user_view(
            user_id=str(user_id),
            view_type=view_type,
            view_id=str(view_id) if view_id else None,
            data=data,
            ttl=ttl or self.get_default_ttl(),
            related_ids=related_ids
        )

        logger.debug(f"Cache SET: user={user_id}, view={view_type}, id={view_id}, ttl={ttl or self.get_default_ttl()}")

    def _invalidate_user_view(
        self,
        user_id: Optional[str] = None,
        view_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ):
        """
        Invalidate cached user views.

        Args:
            user_id: Optional user ID to invalidate
            view_type: Optional view type to invalidate
            entity_type: Optional entity type (e.g., "course_id")
            entity_id: Optional entity ID
        """
        if not self._use_cache():
            return

        self.cache.invalidate_user_views(
            user_id=user_id,
            view_type=view_type,
            entity_type=entity_type,
            entity_id=entity_id
        )

    def get_default_ttl(self) -> int:
        """
        Get default TTL for this view repository.

        Override in subclasses to customize.

        Returns:
            TTL in seconds (default: 5 minutes)
        """
        return 300  # 5 minutes

    def _serialize_dto(self, dto: Any) -> Any:
        """
        Serialize DTO for caching.

        Args:
            dto: DTO object to serialize

        Returns:
            Serialized data (dict or original if no model_dump)
        """
        if hasattr(dto, 'model_dump'):
            return dto.model_dump()
        return dto

    def _serialize_dto_list(self, dtos: List[Any]) -> List[Any]:
        """
        Serialize list of DTOs for caching.

        Args:
            dtos: List of DTO objects

        Returns:
            List of serialized data
        """
        return [self._serialize_dto(dto) for dto in dtos]
