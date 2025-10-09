"""
Base repository pattern implementation with optional caching.

This module provides abstract base classes for the repository pattern,
enabling direct database access with transparent write-through caching.
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any, Type, Set
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import inspect

# Type variable for generic entity type
T = TypeVar('T')


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class NotFoundError(RepositoryError):
    """Exception raised when entity is not found."""
    
    def __init__(self, entity_type: str, entity_id: Any):
        super().__init__(f"{entity_type} with id {entity_id} not found")
        self.entity_type = entity_type
        self.entity_id = entity_id


class DuplicateError(RepositoryError):
    """Exception raised when attempting to create duplicate entity."""
    
    def __init__(self, entity_type: str, criteria: Dict[str, Any]):
        super().__init__(f"{entity_type} already exists with criteria: {criteria}")
        self.entity_type = entity_type
        self.criteria = criteria


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository providing common database operations with optional caching.

    This class implements the repository pattern with transparent write-through caching.
    If cache is provided, read operations check cache first and writes invalidate cache.
    If cache is None, operates as a standard repository without caching.
    """

    def __init__(self, db: Session, model: Type[T], cache=None):
        """
        Initialize repository with database session, model class, and optional cache.

        Args:
            db: SQLAlchemy database session
            model: SQLAlchemy model class
            cache: Optional Cache instance (if None, caching is disabled)
        """
        self.db = db
        self.model = model
        self.cache = cache

    # ========================================================================
    # Cache configuration (override in subclasses if needed)
    # ========================================================================

    @property
    def entity_type(self) -> Optional[str]:
        """
        Get entity type identifier for cache keys.

        Override this in subclasses that use caching.

        Returns:
            Entity type string (e.g., "organization", "course") or None
        """
        return None

    def get_ttl(self) -> int:
        """
        Get TTL for cached entities.

        Override this to set custom TTL per entity type.
        Default: 600 seconds (10 minutes)

        Returns:
            TTL in seconds
        """
        return 600

    def get_entity_tags(self, entity: T) -> Set[str]:
        """
        Get cache tags for an entity.

        Override this in subclasses to define invalidation tags.

        Args:
            entity: Entity instance

        Returns:
            Set of cache tags
        """
        return set()

    def get_list_tags(self, **filters) -> Set[str]:
        """
        Get cache tags for list queries.

        Override this in subclasses to define list query tags.

        Args:
            **filters: Query filters

        Returns:
            Set of cache tags
        """
        return set()

    # ========================================================================
    # Cache helper methods
    # ========================================================================

    def _use_cache(self) -> bool:
        """Check if caching is enabled and entity_type is defined."""
        return self.cache is not None and self.entity_type is not None

    def _serialize_entity(self, entity: T) -> Optional[Dict[str, Any]]:
        """Serialize entity to dictionary for caching."""
        if entity is None:
            return None

        result = {}
        for column in entity.__table__.columns:
            value = getattr(entity, column.name)
            # Convert non-JSON-serializable types
            if value is None:
                result[column.name] = None
            elif hasattr(value, 'isoformat'):  # datetime
                result[column.name] = value.isoformat()
            elif isinstance(value, (dict, list)):  # JSONB fields - already JSON-serializable
                result[column.name] = value
            elif isinstance(value, (str, int, float, bool)):  # Primitives
                result[column.name] = value
            else:
                # For other types (UUID, Enum, etc.), convert to string
                result[column.name] = str(value)
        return result

    def _deserialize_entity(self, data: Dict[str, Any]) -> Optional[T]:
        """
        Deserialize dictionary to entity (detached from session).

        Creates a proper SQLAlchemy instance with all internal state initialized.
        """
        if data is None:
            return None

        try:
            # Try to create instance with no args (most SQLAlchemy models support this)
            instance = self.model()
        except TypeError:
            # If model requires args, use object.__new__ and manually set __dict__
            # This bypasses __init__ but still initializes SQLAlchemy state properly
            from sqlalchemy.orm.state import InstanceState
            from sqlalchemy import inspect

            instance = object.__new__(self.model)
            # Initialize SQLAlchemy's instance state
            InstanceState(instance, inspect(self.model).mapper)

        # Set attributes from cached data
        for key, value in data.items():
            # Skip SQLAlchemy internal attributes
            if not key.startswith('_sa_'):
                # Handle legacy cached JSONB that might be stringified
                # This handles old cached data before the serialization fix
                if key == 'properties' and isinstance(value, str) and value.startswith('{'):
                    try:
                        import json
                        # Try to parse as JSON first
                        value = json.loads(value)
                    except Exception:
                        # If JSON parsing fails, try Python literal eval
                        try:
                            import ast
                            value = ast.literal_eval(value)
                        except Exception:
                            # If all parsing fails, leave as string (will be fixed on next write)
                            pass

                try:
                    setattr(instance, key, value)
                except Exception:
                    # If setting attribute fails, use __dict__ directly
                    instance.__dict__[key] = value

        return instance
    
    def get_by_id(self, entity_id: Any) -> T:
        """
        Get entity by ID (with optional caching).

        Args:
            entity_id: Entity identifier

        Returns:
            Entity instance

        Raises:
            NotFoundError: If entity not found
        """
        entity = self.get_by_id_optional(entity_id)
        if entity is None:
            raise NotFoundError(self.model.__name__, entity_id)
        return entity

    def get_by_id_optional(self, entity_id: Any) -> Optional[T]:
        """
        Get entity by ID, returning None if not found (with optional caching).

        Args:
            entity_id: Entity identifier

        Returns:
            Entity instance or None
        """
        # Try cache first if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, entity_id)
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached)

        # Fetch from DB
        entity = self.db.query(self.model).filter(
            self.model.id == entity_id
        ).first()

        # Cache if enabled and entity found
        if entity and self._use_cache():
            key = self.cache.key(self.entity_type, entity_id)
            tags = self.get_entity_tags(entity)
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity),
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity
    
    def list(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **filters
    ) -> List[T]:
        """
        List entities with optional pagination and filters (with optional caching).

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            **filters: Additional filter criteria

        Returns:
            List of entities
        """
        # Try cache if enabled
        if self._use_cache():
            query_params = {"limit": limit, "offset": offset, **filters}
            key = self.cache.key(self.entity_type, f"list:{hash(frozenset(query_params.items()))}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Fetch from DB
        query = self.db.query(self.model)

        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        # Apply pagination
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        entities = query.all()

        # Cache if enabled
        if self._use_cache():
            query_params = {"limit": limit, "offset": offset, **filters}
            key = self.cache.key(self.entity_type, f"list:{hash(frozenset(query_params.items()))}")
            tags = self.get_list_tags(**filters)
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(key=key, payload=serialized, tags=tags, ttl=self.get_ttl())

        return entities
    
    def create(self, entity: T) -> T:
        """
        Create a new entity and invalidate related caches.

        Args:
            entity: Entity instance to create

        Returns:
            Created entity with updated fields (e.g., ID)

        Raises:
            DuplicateError: If entity violates unique constraints
            RepositoryError: If database operation fails
        """
        try:
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)

            # Invalidate caches if enabled
            if self._use_cache():
                tags = self.get_entity_tags(entity)
                if tags:
                    self.cache.invalidate_tags(*tags)

            return entity
        except IntegrityError as e:
            self.db.rollback()
            raise DuplicateError(
                self.model.__name__,
                self._extract_entity_dict(entity)
            )
        except SQLAlchemyError as e:
            self.db.rollback()
            raise RepositoryError(f"Failed to create {self.model.__name__}: {str(e)}")
    
    def update(self, entity_id: Any, updates: Dict[str, Any]) -> T:
        """
        Update an existing entity and invalidate related caches.

        Args:
            entity_id: Entity identifier
            updates: Dictionary of fields to update

        Returns:
            Updated entity

        Raises:
            NotFoundError: If entity not found
            RepositoryError: If update fails
        """
        entity = self.get_by_id(entity_id)

        try:
            # Apply updates
            for key, value in updates.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            self.db.commit()
            self.db.refresh(entity)

            # Invalidate caches if enabled
            if self._use_cache():
                tags = self.get_entity_tags(entity)
                tags.add(f"{self.entity_type}:{entity_id}")  # Ensure entity key invalidated
                if tags:
                    self.cache.invalidate_tags(*tags)

            return entity
        except SQLAlchemyError as e:
            self.db.rollback()
            raise RepositoryError(f"Failed to update {self.model.__name__}: {str(e)}")
    
    def delete(self, entity_id: Any) -> bool:
        """
        Delete an entity by ID and invalidate related caches.

        Args:
            entity_id: Entity identifier

        Returns:
            True if deletion successful

        Raises:
            NotFoundError: If entity not found
            RepositoryError: If deletion fails
        """
        entity = self.get_by_id(entity_id)

        # Get tags before deletion if caching enabled
        tags = None
        if self._use_cache():
            tags = self.get_entity_tags(entity)
            tags.add(f"{self.entity_type}:{entity_id}")

        try:
            self.db.delete(entity)
            self.db.commit()

            # Invalidate caches if enabled
            if tags:
                self.cache.invalidate_tags(*tags)

            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise RepositoryError(f"Failed to delete {self.model.__name__}: {str(e)}")
    
    def exists(self, entity_id: Any) -> bool:
        """
        Check if entity exists by ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            True if entity exists
        """
        return self.db.query(self.model).filter(
            self.model.id == entity_id
        ).count() > 0
    
    def find_by(self, **criteria) -> List[T]:
        """
        Find entities by multiple criteria (with optional caching).

        Args:
            **criteria: Search criteria as keyword arguments

        Returns:
            List of matching entities
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"find_by:{hash(frozenset(criteria.items()))}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return [self._deserialize_entity(item) for item in cached]

        # Fetch from DB
        query = self.db.query(self.model)

        for key, value in criteria.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        entities = query.all()

        # Cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"find_by:{hash(frozenset(criteria.items()))}")
            tags = self.get_list_tags(**criteria)
            serialized = [self._serialize_entity(e) for e in entities]
            self.cache.set_with_tags(key=key, payload=serialized, tags=tags, ttl=self.get_ttl())

        return entities

    def find_one_by(self, **criteria) -> Optional[T]:
        """
        Find single entity by criteria (with optional caching).

        Args:
            **criteria: Search criteria as keyword arguments

        Returns:
            First matching entity or None
        """
        # Try cache if enabled
        if self._use_cache():
            key = self.cache.key(self.entity_type, f"find_one_by:{hash(frozenset(criteria.items()))}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached)

        # Fetch from DB
        query = self.db.query(self.model)

        for key, value in criteria.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)

        entity = query.first()

        # Cache if enabled and entity found
        if entity and self._use_cache():
            key = self.cache.key(self.entity_type, f"find_one_by:{hash(frozenset(criteria.items()))}")
            tags = self.get_entity_tags(entity)
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity),
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity
    
    def count(self, **criteria) -> int:
        """
        Count entities matching criteria.
        
        Args:
            **criteria: Filter criteria as keyword arguments
            
        Returns:
            Number of matching entities
        """
        query = self.db.query(self.model)
        
        for key, value in criteria.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        
        return query.count()
    
    def flush(self) -> None:
        """Flush pending changes without committing."""
        self.db.flush()
    
    def commit(self) -> None:
        """Commit the current transaction."""
        self.db.commit()
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.db.rollback()
    
    def _extract_entity_dict(self, entity: T) -> Dict[str, Any]:
        """
        Extract entity attributes as dictionary.
        
        Args:
            entity: Entity instance
            
        Returns:
            Dictionary of entity attributes
        """
        # Use SQLAlchemy inspection if available
        try:
            mapper = inspect(entity)
            return {
                col.key: getattr(entity, col.key)
                for col in mapper.attrs
                if hasattr(entity, col.key)
            }
        except Exception:
            # Fallback to simple attribute extraction
            return {
                attr: getattr(entity, attr)
                for attr in dir(entity)
                if not attr.startswith('_') and not callable(getattr(entity, attr))
            }