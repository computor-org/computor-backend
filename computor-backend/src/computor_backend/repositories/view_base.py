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


def _aggregate_grading_status(statuses: List[str]) -> Optional[str]:
    """
    Aggregate multiple grading statuses following priority rules.

    Rules:
    1. If ANY 'correction_necessary' exists -> 'correction_necessary'
    2. Else if ANY 'improvement_possible' exists -> 'improvement_possible'
    3. Else if ALL are 'corrected' -> 'corrected'
    4. Else -> 'not_reviewed' (mix of corrected/not_reviewed, or all not_reviewed, or empty)

    Args:
        statuses: List of grading status strings (can include None values)

    Returns:
        Aggregated status string, or None if no valid statuses
    """
    # Filter out None values
    valid_statuses = [s for s in statuses if s is not None]

    if not valid_statuses:
        return None

    # Check for correction_necessary (highest priority)
    if "correction_necessary" in valid_statuses:
        return "correction_necessary"

    # Check for improvement_possible
    if "improvement_possible" in valid_statuses:
        return "improvement_possible"

    # Check if ALL are corrected
    if all(s == "corrected" for s in valid_statuses):
        return "corrected"

    # Default: not_reviewed (mix or all not_reviewed)
    return "not_reviewed"


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

    def __init__(self, cache: Optional[Cache] = None, user_id: Optional[str] = None):
        """
        Initialize view repository.

        Args:
            cache: Optional Cache instance (enables caching)
            user_id: Optional user ID for audit tracking in DB sessions
        """
        self._db: Optional[Session] = None
        self._owns_db: bool = False
        self._user_id = user_id
        self.cache = cache

    @property
    def db(self) -> Session:
        """
        Get or create database session on-demand.

        The connection is only created when this property is accessed,
        enabling cache-first patterns where no DB connection is needed on cache hits.

        Returns:
            Database session
        """
        if self._db is None:
            from ..database import get_db
            logger.debug(f"ViewRepository: Creating DB connection on-demand (user_id={self._user_id})")
            self._db = next(get_db(self._user_id))
            self._owns_db = True
        return self._db

    def close(self):
        """Close the database session if we created it."""
        if self._owns_db and self._db is not None:
            self._db.close()
            self._db = None
            self._owns_db = False
            logger.debug("ViewRepository: Closed DB connection")

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

    def _aggregate_unit_statuses(
        self,
        course_contents: List[Any],
        user_id: str,
    ) -> List[Any]:
        """
        Aggregate status and unreviewed_count for unit-like course contents from their descendants.

        Units (non-submittable course contents) don't have their own submission_group,
        so their status is derived from their descendant submittable contents.

        Status aggregation rules:
        1. If ANY 'correction_necessary' exists -> 'correction_necessary'
        2. Else if ANY 'improvement_possible' exists -> 'improvement_possible'
        3. Else if ALL are 'corrected' -> 'corrected'
        4. Else -> 'not_reviewed' (mix or all not_reviewed)

        unreviewed_count aggregation: Sum of all descendant submittable contents' unreviewed_count

        Args:
            course_contents: List of course contents with status already set for submittables
            user_id: User ID (needed for fallback DB query)

        Returns:
            Same list with unit statuses and unreviewed_count aggregated from descendants
        """
        if not course_contents:
            return course_contents

        # Build a map of path -> course_content for quick lookup
        path_to_content: Dict[str, Any] = {
            str(cc.path): cc for cc in course_contents
        }

        # Identify units (non-submittable) - they have no submission_group
        # and potentially no status set yet
        units = [cc for cc in course_contents if cc.submission_group is None]

        # For each unit, find descendants and aggregate their statuses and unreviewed_count
        for unit in units:
            unit_path = str(unit.path)
            descendant_statuses: List[str] = []
            total_unreviewed_count = 0

            # Find all descendants by checking if their path starts with unit_path
            # In ltree, a.b.c is a descendant of a.b if a.b.c starts with a.b.
            for path, cc in path_to_content.items():
                # Skip self
                if path == unit_path:
                    continue

                # Check if this is a descendant (path starts with unit_path + '.')
                if path.startswith(unit_path + '.'):
                    # Only collect status from submittable contents (those with submission_group)
                    # If submission_group exists but status is None, treat as not_reviewed
                    if cc.submission_group is not None:
                        descendant_statuses.append(cc.status if cc.status else "not_reviewed")
                        # Sum up unreviewed_count from descendants
                        total_unreviewed_count += getattr(cc, 'unreviewed_count', 0) or 0

            # Aggregate and set the unit's status
            if descendant_statuses:
                unit.status = _aggregate_grading_status(descendant_statuses)
                unit.unreviewed_count = total_unreviewed_count
            else:
                # No descendants in result set - fall back to DB query
                # This happens when filtering by path/id returns only the unit without descendants
                aggregated = self._aggregate_single_unit_status_for_list(user_id, unit)
                if isinstance(aggregated, tuple):
                    unit.status, unit.unreviewed_count = aggregated
                else:
                    unit.status = aggregated
                    unit.unreviewed_count = 0

        return course_contents

    def _aggregate_single_unit_status_for_list(
        self,
        user_id: str,
        course_content: Any,
    ) -> tuple:
        """
        Aggregate status and unreviewed_count for a single unit from DB when descendants aren't in result set.

        This is a fallback method for when a query returns only a unit without its
        descendants (e.g., filtering by path). It queries the DB to find all
        descendants and aggregate their statuses and unreviewed counts.

        Args:
            user_id: User ID for the query
            course_content: The unit course content to aggregate status for

        Returns:
            Tuple of (aggregated_status, total_unreviewed_count)
        """
        from computor_backend.repositories.course_content import user_course_content_list_query
        from sqlalchemy import text

        unit_path = str(course_content.path)

        # Get all course contents for this user in the same course
        # The query already joins to the user's submission group
        query = user_course_content_list_query(user_id, self.db)
        query = query.filter(text("course_content.course_id = :course_id"))
        query = query.params(course_id=str(course_content.course_id))

        all_contents = query.all()

        # Find descendants and collect their statuses
        # Use the status from the query result tuple which is already user-specific
        descendant_statuses: List[str] = []
        total_unreviewed_count = 0
        status_lookup = {
            0: "not_reviewed",
            1: "corrected",
            2: "correction_necessary",
            3: "improvement_possible"
        }

        for row in all_contents:
            course_content_obj = row[0]
            row_path = str(course_content_obj.path)

            # Skip self and non-descendants
            if row_path == unit_path or not row_path.startswith(unit_path + '.'):
                continue

            # row[3] is submission_group, row[5] is submission_status_int from the query
            # row[10] is is_unreviewed from the query
            submission_group = row[3]
            submission_status_int = row[5] if len(row) > 5 else None
            is_unreviewed = row[10] if len(row) > 10 else 0

            # Only collect from submittable contents (those with submission_group)
            # If submission_group exists but status is None, treat as not_reviewed
            if submission_group is not None:
                status_str = status_lookup.get(submission_status_int, "not_reviewed") if submission_status_int is not None else "not_reviewed"
                descendant_statuses.append(status_str)
                total_unreviewed_count += is_unreviewed or 0

        if descendant_statuses:
            return (_aggregate_grading_status(descendant_statuses), total_unreviewed_count)

        return (None, 0)
