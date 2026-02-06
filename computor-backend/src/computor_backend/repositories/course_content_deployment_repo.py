"""
CourseContentDeployment repository for database access with cache invalidation.

This module provides the CourseContentDeploymentRepository class that handles
all database operations for CourseContentDeployment entities with automatic cache invalidation.
"""

from typing import List, Optional, Set
from uuid import UUID
from sqlalchemy.orm import Session

from .base import BaseRepository
from ..model.deployment import CourseContentDeployment


class CourseContentDeploymentRepository(BaseRepository[CourseContentDeployment]):
    """
    Repository for CourseContentDeployment entity with automatic cache invalidation.

    Handles deployment CRUD operations and ensures all related caches
    (course content views, example version views, deployment status caches) are properly invalidated.
    """

    def __init__(self, db: Session, cache=None):
        """
        Initialize course content deployment repository.

        Args:
            db: SQLAlchemy session
            cache: Optional Cache instance (enables transparent caching)
        """
        super().__init__(db, CourseContentDeployment, cache)

    # ========================================================================
    # Cache configuration
    # ========================================================================

    @property
    def entity_type(self) -> str:
        """Entity type identifier for cache keys."""
        return "course_content_deployment"

    def get_ttl(self) -> int:
        """Deployments change during deployment operations - use 5 minute TTL."""
        return 300  # 5 minutes

    def get_entity_tags(self, entity: CourseContentDeployment) -> Set[str]:
        """
        Get cache tags for course content deployment.

        Tags:
        - course_content_deployment:{id} - The specific deployment
        - course_content_deployment:list - All deployment list queries
        - course_content:{content_id} - Invalidate content-level caches
        - course_content_deployment:content:{content_id} - Deployment for this content
        - example_version:{version_id} - Invalidate version-level caches
        - course_content_deployment:version:{version_id} - Deployments using this version
        - course_content_deployment:status:{status} - Deployments with this status
        - course_content_deployment:example_identifier:{identifier} - Deployments of this example
        """
        tags = {
            f"course_content_deployment:{entity.id}",
            "course_content_deployment:list",
        }

        if entity.course_content_id:
            tags.add(f"course_content_deployment:content:{entity.course_content_id}")
            tags.add(f"course_content:{entity.course_content_id}")

        if entity.example_version_id:
            tags.add(f"course_content_deployment:version:{entity.example_version_id}")
            tags.add(f"example_version:{entity.example_version_id}")

        if entity.deployment_status:
            tags.add(f"course_content_deployment:status:{entity.deployment_status}")

        if entity.example_identifier:
            tags.add(f"course_content_deployment:example_identifier:{entity.example_identifier}")

        if entity.workflow_id:
            tags.add(f"course_content_deployment:workflow:{entity.workflow_id}")

        return tags

    def get_list_tags(self, **filters) -> Set[str]:
        """Get cache tags for list queries."""
        tags = {"course_content_deployment:list"}

        if "course_content_id" in filters:
            tags.add(f"course_content_deployment:content:{filters['course_content_id']}")
            tags.add(f"course_content:{filters['course_content_id']}")

        if "example_version_id" in filters:
            tags.add(f"course_content_deployment:version:{filters['example_version_id']}")
            tags.add(f"example_version:{filters['example_version_id']}")

        if "deployment_status" in filters:
            tags.add(f"course_content_deployment:status:{filters['deployment_status']}")

        if "example_identifier" in filters:
            tags.add(f"course_content_deployment:example_identifier:{filters['example_identifier']}")

        if "workflow_id" in filters:
            tags.add(f"course_content_deployment:workflow:{filters['workflow_id']}")

        return tags

    # ========================================================================
    # Specialized queries
    # ========================================================================

    def find_by_content(self, content_id: str | UUID) -> Optional[CourseContentDeployment]:
        """
        Find deployment for a course content.

        Args:
            content_id: Course content identifier

        Returns:
            CourseContentDeployment if exists, None otherwise (one deployment per content)
        """
        return self.db.query(CourseContentDeployment).filter(
            CourseContentDeployment.course_content_id == str(content_id)
        ).first()

    def find_latest_for_course_content(self, content_id: str | UUID) -> Optional[CourseContentDeployment]:
        """
        Find the latest deployment for a course content (ordered by assigned_at desc).

        Uses caching when enabled. The cache key includes 'latest' to differentiate
        from the simple find_by_content lookup.

        Args:
            content_id: Course content identifier

        Returns:
            Most recent CourseContentDeployment if exists, None otherwise
        """
        content_id_str = str(content_id)

        if self._use_cache():
            key = self.cache.key(self.entity_type, f"latest:content:{content_id_str}")
            cached = self.cache.get_by_key(key)
            if cached is not None:
                return self._deserialize_entity(cached) if cached else None

        entity = self.db.query(CourseContentDeployment).filter(
            CourseContentDeployment.course_content_id == content_id_str
        ).order_by(CourseContentDeployment.assigned_at.desc()).first()

        if self._use_cache():
            key = self.cache.key(self.entity_type, f"latest:content:{content_id_str}")
            tags = self.get_entity_tags(entity) if entity else {f"course_content_deployment:content:{content_id_str}"}
            self.cache.set_with_tags(
                key=key,
                payload=self._serialize_entity(entity) if entity else None,
                tags=tags,
                ttl=self.get_ttl()
            )

        return entity

    def find_by_example_version(self, version_id: str | UUID) -> List[CourseContentDeployment]:
        """
        Find all deployments using a specific example version.

        Args:
            version_id: Example version identifier

        Returns:
            List of deployments using this version
        """
        return self.find_by(example_version_id=str(version_id))

    def find_by_status(self, status: str) -> List[CourseContentDeployment]:
        """
        Find all deployments with a specific status.

        Args:
            status: Deployment status (pending, deploying, deployed, failed, unassigned)

        Returns:
            List of deployments with this status
        """
        return self.find_by(deployment_status=status)

    def find_pending_deployments(self) -> List[CourseContentDeployment]:
        """
        Find all pending deployments.

        Returns:
            List of deployments with status 'pending'
        """
        return self.find_by_status("pending")

    def find_failed_deployments(self) -> List[CourseContentDeployment]:
        """
        Find all failed deployments.

        Returns:
            List of deployments with status 'failed'
        """
        return self.find_by_status("failed")

    def find_by_workflow(self, workflow_id: str) -> List[CourseContentDeployment]:
        """
        Find deployments associated with a Temporal workflow.

        Args:
            workflow_id: Temporal workflow identifier

        Returns:
            List of deployments for this workflow
        """
        return self.find_by(workflow_id=workflow_id)

    def find_by_example_identifier(self, example_identifier: str) -> List[CourseContentDeployment]:
        """
        Find deployments of a specific example identifier.

        Args:
            example_identifier: Example identifier (ltree format)

        Returns:
            List of deployments for this example
        """
        return self.find_by(example_identifier=example_identifier)

    def find_deployed_versions(self) -> List[CourseContentDeployment]:
        """
        Find all successfully deployed deployments.

        Returns:
            List of deployments with status 'deployed'
        """
        return self.find_by_status("deployed")

    def get_deployment_statistics(self) -> dict:
        """
        Get deployment statistics across all deployments.

        Returns:
            Dictionary with counts by status
        """
        from sqlalchemy import func

        results = self.db.query(
            CourseContentDeployment.deployment_status,
            func.count(CourseContentDeployment.id)
        ).group_by(CourseContentDeployment.deployment_status).all()

        return {status: count for status, count in results}
