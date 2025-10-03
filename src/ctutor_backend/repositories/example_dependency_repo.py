"""
ExampleDependency repository for database access with cache invalidation.

This module provides the ExampleDependencyRepository class that handles
all database operations for ExampleDependency entities with automatic cache invalidation.
"""

from typing import List, Optional, Set
from uuid import UUID
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.example import ExampleDependency


class ExampleDependencyRepository(BaseRepository[ExampleDependency]):
    """
    Repository for ExampleDependency entity with automatic cache invalidation.

    Handles example dependency CRUD operations and ensures all related caches
    (example views, dependency graphs) are properly invalidated.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize example dependency repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, ExampleDependency, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "example_dependency"

    def get_ttl(self) -> int:
        """Dependencies are relatively stable - use 30 minute TTL."""
        return 1800  # 30 minutes

    def get_entity_tags(self, entity: ExampleDependency) -> Set[str]:
        """
        Get cache tags for example dependency.

        Tags:
        - example_dependency:{id} - The specific dependency
        - example_dependency:list - All dependency list queries
        - example:{example_id} - Invalidate example-level caches (for the dependent)
        - example:{depends_id} - Invalidate example-level caches (for the dependency)
        - example_dependency:example:{example_id} - Dependencies of this example
        - example_dependency:depends:{depends_id} - Examples depending on this
        """
        tags = {
            f"example_dependency:{entity.id}",
            "example_dependency:list",
        }

        if entity.example_id:
            tags.add(f"example_dependency:example:{entity.example_id}")
            tags.add(f"example:{entity.example_id}")

        if entity.depends_id:
            tags.add(f"example_dependency:depends:{entity.depends_id}")
            tags.add(f"example:{entity.depends_id}")

        # Tag by version constraint for constraint-specific queries
        if entity.version_constraint:
            tags.add(f"example_dependency:constraint:{entity.version_constraint}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"example_dependency:list"}

        if "example_id" in filters:
            tags.add(f"example_dependency:example:{filters['example_id']}")
            tags.add(f"example:{filters['example_id']}")

        if "depends_id" in filters:
            tags.add(f"example_dependency:depends:{filters['depends_id']}")
            tags.add(f"example:{filters['depends_id']}")

        if "version_constraint" in filters:
            tags.add(f"example_dependency:constraint:{filters['version_constraint']}")

        return tags

    # ========================================================================
    # Specialized queries
    # ========================================================================

    def find_dependencies_of(self, example_id: str | UUID) -> List[ExampleDependency]:
        """
        Find all dependencies of an example (what this example depends on).

        Args:
            example_id: Example identifier

        Returns:
            List of dependencies where example_id is the dependent
        """
        return self.find_by(example_id=str(example_id))

    def find_dependents_of(self, example_id: str | UUID) -> List[ExampleDependency]:
        """
        Find all examples that depend on this example.

        Args:
            example_id: Example identifier

        Returns:
            List of dependencies where example_id is the dependency
        """
        return self.find_by(depends_id=str(example_id))

    def find_dependency_between(
        self,
        example_id: str | UUID,
        depends_id: str | UUID
    ) -> Optional[ExampleDependency]:
        """
        Find a specific dependency relationship.

        Args:
            example_id: Dependent example identifier
            depends_id: Dependency example identifier

        Returns:
            ExampleDependency if exists, None otherwise
        """
        return self.db.query(ExampleDependency).filter(
            ExampleDependency.example_id == str(example_id),
            ExampleDependency.depends_id == str(depends_id)
        ).first()

    def has_circular_dependency(
        self,
        example_id: str | UUID,
        depends_id: str | UUID
    ) -> bool:
        """
        Check if adding a dependency would create a circular dependency.

        Args:
            example_id: Dependent example identifier
            depends_id: Dependency example identifier

        Returns:
            True if circular dependency would be created, False otherwise
        """
        # Check if depends_id already depends on example_id (directly or transitively)
        visited = set()
        to_check = [str(depends_id)]

        while to_check:
            current = to_check.pop()
            if current in visited:
                continue

            if current == str(example_id):
                return True

            visited.add(current)

            # Get dependencies of current
            dependencies = self.find_dependencies_of(current)
            to_check.extend([str(dep.depends_id) for dep in dependencies])

        return False

    def get_dependency_tree(self, example_id: str | UUID) -> List[ExampleDependency]:
        """
        Get the complete dependency tree for an example (transitive dependencies).

        Args:
            example_id: Example identifier

        Returns:
            List of all transitive dependencies
        """
        visited = set()
        all_dependencies = []
        to_check = [str(example_id)]

        while to_check:
            current = to_check.pop()
            if current in visited:
                continue

            visited.add(current)

            # Get direct dependencies
            dependencies = self.find_dependencies_of(current)
            all_dependencies.extend(dependencies)

            # Add dependency IDs to check
            to_check.extend([str(dep.depends_id) for dep in dependencies])

        return all_dependencies

    def find_by_constraint(self, version_constraint: str) -> List[ExampleDependency]:
        """
        Find all dependencies with a specific version constraint.

        Args:
            version_constraint: Version constraint string (e.g., '>=1.2.0', '^2.1.0')

        Returns:
            List of dependencies with this constraint
        """
        return self.find_by(version_constraint=version_constraint)

    def find_unconstrained_dependencies(self) -> List[ExampleDependency]:
        """
        Find all dependencies without version constraints (latest version).

        Returns:
            List of dependencies with version_constraint=None
        """
        return self.db.query(ExampleDependency).filter(
            ExampleDependency.version_constraint.is_(None)
        ).all()
