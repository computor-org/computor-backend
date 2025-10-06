"""
ExampleVersion repository for database access with cache invalidation.

This module provides the ExampleVersionRepository class that handles
all database operations for ExampleVersion entities with automatic cache invalidation.
"""

from typing import List, Optional, Set
from uuid import UUID
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.example import ExampleVersion


class ExampleVersionRepository(BaseRepository[ExampleVersion]):
    """
    Repository for ExampleVersion entity with automatic cache invalidation.

    Handles example version CRUD operations and ensures all related caches
    (example views, deployment caches) are properly invalidated.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize example version repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, ExampleVersion, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "example_version"

    def get_ttl(self) -> int:
        """Example versions are immutable once created - use 1 hour TTL."""
        return 3600  # 1 hour

    def get_entity_tags(self, entity: ExampleVersion) -> Set[str]:
        """
        Get cache tags for example version.

        Tags:
        - example_version:{id} - The specific version
        - example_version:list - All version list queries
        - example:{example_id} - Invalidate example-level caches
        - example_version:example:{example_id} - Versions for this example
        - course_content_deployment:example_version:{id} - Deployments using this version
        """
        tags = {
            f"example_version:{entity.id}",
            "example_version:list",
        }

        if entity.example_id:
            tags.add(f"example_version:example:{entity.example_id}")
            tags.add(f"example:{entity.example_id}")
            # Invalidate deployment caches that might use this version
            tags.add(f"course_content_deployment:example_version:{entity.id}")

        # Tag by version_tag for version-specific queries
        if entity.version_tag:
            tags.add(f"example_version:tag:{entity.version_tag}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"example_version:list"}

        if "example_id" in filters:
            tags.add(f"example_version:example:{filters['example_id']}")
            tags.add(f"example:{filters['example_id']}")

        if "version_tag" in filters:
            tags.add(f"example_version:tag:{filters['version_tag']}")

        return tags

    # ========================================================================
    # Specialized queries
    # ========================================================================

    def find_by_example(self, example_id: str | UUID) -> List[ExampleVersion]:
        """
        Find all versions of an example.

        Args:
            example_id: Example identifier

        Returns:
            List of example versions ordered by version_number descending
        """
        query = self.db.query(ExampleVersion).filter(
            ExampleVersion.example_id == str(example_id)
        ).order_by(ExampleVersion.version_number.desc())

        return query.all()

    def find_by_version_tag(
        self,
        example_id: str | UUID,
        version_tag: str
    ) -> Optional[ExampleVersion]:
        """
        Find a specific version by tag.

        Args:
            example_id: Example identifier
            version_tag: Version tag (e.g., 'v1.0', 'v2.0-beta')

        Returns:
            ExampleVersion if found, None otherwise
        """
        return self.db.query(ExampleVersion).filter(
            ExampleVersion.example_id == str(example_id),
            ExampleVersion.version_tag == version_tag
        ).first()

    def find_latest_version(self, example_id: str | UUID) -> Optional[ExampleVersion]:
        """
        Find the latest version of an example.

        Args:
            example_id: Example identifier

        Returns:
            Latest ExampleVersion if exists, None otherwise
        """
        return self.db.query(ExampleVersion).filter(
            ExampleVersion.example_id == str(example_id)
        ).order_by(ExampleVersion.version_number.desc()).first()

    def find_by_version_number(
        self,
        example_id: str | UUID,
        version_number: int
    ) -> Optional[ExampleVersion]:
        """
        Find a specific version by number.

        Args:
            example_id: Example identifier
            version_number: Sequential version number

        Returns:
            ExampleVersion if found, None otherwise
        """
        return self.db.query(ExampleVersion).filter(
            ExampleVersion.example_id == str(example_id),
            ExampleVersion.version_number == version_number
        ).first()

    def find_by_storage_path(self, storage_path: str) -> Optional[ExampleVersion]:
        """
        Find version by storage path.

        Args:
            storage_path: Path in storage system

        Returns:
            ExampleVersion if found, None otherwise
        """
        return self.db.query(ExampleVersion).filter(
            ExampleVersion.storage_path == storage_path
        ).first()

    def get_next_version_number(self, example_id: str | UUID) -> int:
        """
        Get the next version number for an example.

        Args:
            example_id: Example identifier

        Returns:
            Next sequential version number (1 if no versions exist)
        """
        latest = self.find_latest_version(example_id)
        return (latest.version_number + 1) if latest else 1
