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
    # Overridden CRUD methods for cascading cache invalidation
    # ========================================================================

    def create(self, entity: ExampleVersion) -> ExampleVersion:
        """
        Create example version and cascade cache invalidation to deployments.

        When a new ExampleVersion is created, any CourseContentDeployment
        that references the parent Example needs cache invalidation so
        student/tutor views show updated deployment information.

        Args:
            entity: ExampleVersion to create

        Returns:
            Created ExampleVersion
        """
        import logging
        logger = logging.getLogger(__name__)

        # Create the entity using parent's create method (handles normal cache invalidation)
        result = super().create(entity)

        # CRITICAL: Cascade invalidation to course_content deployments
        if self.cache and result.example_id:
            from ..model.deployment import CourseContentDeployment

            # Find all deployments that reference this example (by example_identifier)
            # We need to check the parent Example's identifier
            from ..model.example import Example
            example = self.db.query(Example).filter(Example.id == result.example_id).first()

            if example and example.identifier:
                # Find all deployments using this example's identifier
                # Don't convert to str - use the Ltree object directly for proper comparison
                deployments = self.db.query(CourseContentDeployment).filter(
                    CourseContentDeployment.example_identifier == example.identifier
                ).all()

                if deployments:
                    # Collect unique course_content_ids to invalidate
                    tags_to_invalidate = set()
                    for deployment in deployments:
                        if deployment.course_content_id:
                            tags_to_invalidate.add(f"course_content:{deployment.course_content_id}")

                    # Invalidate all affected course_content caches
                    if tags_to_invalidate:
                        self.cache.invalidate_tags(*tags_to_invalidate)
                        logger.info(
                            f"Invalidated {len(tags_to_invalidate)} course_content caches "
                            f"after creating example version {result.id} for example {example.identifier}"
                        )

        return result

    def update(self, entity_id, updates: dict) -> ExampleVersion:
        """
        Update example version and cascade cache invalidation to deployments.

        Args:
            entity_id: ExampleVersion ID
            updates: Dictionary of fields to update

        Returns:
            Updated ExampleVersion
        """
        import logging
        logger = logging.getLogger(__name__)

        # Get the entity before update to check if it affects deployments
        entity = self.get_by_id(entity_id)
        if not entity:
            raise ValueError(f"ExampleVersion {entity_id} not found")

        # Update using parent's method (handles normal cache invalidation)
        result = super().update(entity_id, updates)

        # CRITICAL: Cascade invalidation to course_content deployments if relevant fields changed
        # (e.g., version_tag, status, storage_path)
        if self.cache and entity.example_id:
            from ..model.deployment import CourseContentDeployment
            from ..model.example import Example

            example = self.db.query(Example).filter(Example.id == entity.example_id).first()

            if example and example.identifier:
                # Don't convert to str - use the Ltree object directly for proper comparison
                deployments = self.db.query(CourseContentDeployment).filter(
                    CourseContentDeployment.example_identifier == example.identifier
                ).all()

                if deployments:
                    tags_to_invalidate = set()
                    for deployment in deployments:
                        if deployment.course_content_id:
                            tags_to_invalidate.add(f"course_content:{deployment.course_content_id}")

                    if tags_to_invalidate:
                        self.cache.invalidate_tags(*tags_to_invalidate)
                        logger.info(
                            f"Invalidated {len(tags_to_invalidate)} course_content caches "
                            f"after updating example version {result.id}"
                        )

        return result

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

    def find_latest_version(self, example_id: str | UUID, with_relationships: bool = False) -> Optional[ExampleVersion]:
        """
        Find the latest version of an example.

        Args:
            example_id: Example identifier
            with_relationships: If True, eagerly load example and repository relationships

        Returns:
            Latest ExampleVersion if exists, None otherwise
        """
        query = self.db.query(ExampleVersion)

        if with_relationships:
            from sqlalchemy.orm import joinedload
            from ..model.example import Example
            query = query.options(
                joinedload(ExampleVersion.example).joinedload(Example.repository)
            )

        return query.filter(
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

    def get_with_relationships(self, version_id: str | UUID) -> Optional[ExampleVersion]:
        """
        Get an ExampleVersion with example and repository relationships eagerly loaded.

        This is useful for operations that need to access version.example.repository
        without triggering lazy loading issues.

        Args:
            version_id: ExampleVersion identifier

        Returns:
            ExampleVersion with relationships loaded, or None if not found
        """
        from sqlalchemy.orm import joinedload
        from ..model.example import Example, ExampleRepository

        return self.db.query(ExampleVersion).options(
            joinedload(ExampleVersion.example).joinedload(Example.repository)
        ).filter(
            ExampleVersion.id == str(version_id)
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
