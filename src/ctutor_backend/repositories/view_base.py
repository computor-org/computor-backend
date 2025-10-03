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
import json
import hashlib

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

    def _get_cached_query_view(
        self,
        user_id: str,
        view_type: str,
        params: Any
    ) -> Optional[Any]:
        """
        Get cached view data for a query with parameters.

        This method creates a cache key from the query parameters, making
        cache invalidation more precise and preventing cache pollution.

        Args:
            user_id: User ID
            view_type: View type (e.g., "course_contents", "courses")
            params: Query parameters DTO (e.g., CourseContentQuery)

        Returns:
            Cached data or None

        Example:
            params = CourseContentQuery(course_id="123", limit=10)
            cached = self._get_cached_query_view(user_id, "course_contents", params)
            # Cache key: "user:user123:course_contents:course_id:123|limit:10"
        """
        if not self._use_cache():
            return None

        # Serialize params into stable cache key component
        params_key = self._serialize_query_params(params)
        full_view_type = f"{view_type}:{params_key}"

        cached = self.cache.get_user_view(
            user_id=str(user_id),
            view_type=full_view_type
        )

        if cached is not None:
            logger.debug(f"Cache HIT: user={user_id}, view={full_view_type}")
        else:
            logger.debug(f"Cache MISS: user={user_id}, view={full_view_type}")

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

    def _set_cached_query_view(
        self,
        user_id: str,
        view_type: str,
        params: Any,
        data: Any,
        ttl: Optional[int] = None,
        related_ids: Optional[Dict[str, str]] = None
    ):
        """
        Cache view data for a query with parameters.

        This method creates a cache key from the query parameters, making
        cache invalidation more precise. Related entity IDs are extracted
        from params and can be supplemented with additional related_ids.

        Args:
            user_id: User ID
            view_type: View type (e.g., "course_contents", "courses")
            params: Query parameters DTO (e.g., CourseContentQuery)
            data: Data to cache
            ttl: Time-to-live in seconds
            related_ids: Additional related entity IDs for tag generation

        Example:
            params = CourseContentQuery(course_id="123", limit=10)
            self._set_cached_query_view(user_id, "course_contents", params, data)
            # Cache key: "user:user123:course_contents:course_id:123|limit:10"
            # Tags: ["course_id:123"]
        """
        if not self._use_cache():
            return

        # Serialize params into stable cache key component
        params_key = self._serialize_query_params(params)
        full_view_type = f"{view_type}:{params_key}"

        # Extract related IDs from params for tagging
        auto_related_ids = self._extract_related_ids_from_params(params)

        # Merge auto-extracted IDs with manually provided ones
        all_related_ids = {**auto_related_ids, **(related_ids or {})}

        self.cache.set_user_view(
            user_id=str(user_id),
            view_type=full_view_type,
            data=data,
            ttl=ttl or self.get_default_ttl(),
            related_ids=all_related_ids if all_related_ids else None
        )

        logger.debug(f"Cache SET: user={user_id}, view={full_view_type}, tags={list(all_related_ids.keys()) if all_related_ids else []}, ttl={ttl or self.get_default_ttl()}")

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

    def _serialize_query_params(self, params: Any, use_hash: bool = True) -> str:
        """
        Serialize query parameters into a stable, deterministic cache key component.

        This method converts Query DTOs (like CourseContentQuery, CourseStudentQuery, etc.)
        into a stable string that can be used as part of a Redis cache key.

        Args:
            params: Query DTO object (e.g., CourseContentQuery)
            use_hash: If True, return a SHA256 hash of the params (shorter keys).
                     If False, return human-readable serialization (for debugging).

        Returns:
            Stable string representation of query parameters

        Example (use_hash=False):
            CourseContentQuery(course_id="123", limit=10, skip=0)
            -> "course_id:123|limit:10|skip:0"

        Example (use_hash=True):
            CourseContentQuery(course_id="123", limit=10, skip=0)
            -> "a3f2e8b..." (SHA256 hash of stable JSON)
        """
        if params is None:
            return "default"

        # Get dict representation (exclude None values to make keys shorter)
        if hasattr(params, 'model_dump'):
            params_dict = params.model_dump(exclude_none=True, exclude_unset=True)
        elif isinstance(params, dict):
            params_dict = {k: v for k, v in params.items() if v is not None}
        else:
            # Fallback for non-Pydantic objects
            return str(params)

        if not params_dict:
            return "default"

        if use_hash:
            # Create stable JSON string and hash it
            # Sort keys for deterministic ordering
            stable_json = json.dumps(params_dict, sort_keys=True, separators=(',', ':'))
            # Use SHA256 for uniqueness (take first 16 chars for brevity)
            hash_digest = hashlib.sha256(stable_json.encode('utf-8')).hexdigest()
            return hash_digest[:16]  # 16 chars should be sufficient for uniqueness
        else:
            # Create human-readable key (good for debugging)
            # Sort keys for deterministic ordering
            sorted_items = sorted(params_dict.items())
            parts = []
            for key, value in sorted_items:
                # Convert value to string, handling complex types
                if isinstance(value, (list, dict)):
                    # For complex types, use compact JSON
                    value_str = json.dumps(value, sort_keys=True, separators=(',', ':'))
                else:
                    value_str = str(value)
                parts.append(f"{key}:{value_str}")

            return "|".join(parts)

    def _extract_related_ids_from_params(self, params: Any) -> Dict[str, str]:
        """
        Extract entity IDs from query parameters for cache tagging.

        This enables automatic cache invalidation when entities change.
        For example, if params has course_id="123", this creates a tag
        so the cache can be invalidated when course 123 changes.

        Args:
            params: Query parameters DTO

        Returns:
            Dict of entity_type -> entity_id for tagging

        Example:
            CourseContentQuery(course_id="123", course_content_type_id="456")
            -> {"course_id": "123", "course_content_type_id": "456"}
        """
        if params is None:
            return {}

        # Get dict representation
        if hasattr(params, 'model_dump'):
            params_dict = params.model_dump(exclude_none=True, exclude_unset=True)
        elif isinstance(params, dict):
            params_dict = {k: v for k, v in params.items() if v is not None}
        else:
            return {}

        # Extract fields that end with _id (entity references)
        related_ids = {}
        for key, value in params_dict.items():
            # Only extract ID fields (not pagination, filters, etc.)
            if key.endswith('_id') and value is not None:
                # Convert to string for consistent tagging
                related_ids[key] = str(value)

        return related_ids
