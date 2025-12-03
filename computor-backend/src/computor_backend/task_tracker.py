"""
Redis-based task tracker for permission-aware task access.

This module provides task tracking with permission tags, allowing non-admin
users to query tasks they have access to based on user_id, course_id, or
organization_id context.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import redis.asyncio as aioredis

from computor_types.tasks import TaskTrackerEntry
from computor_backend.permissions.principal import Principal, course_role_hierarchy

logger = logging.getLogger(__name__)

# Default TTL for task entries (24 hours)
DEFAULT_TASK_TTL = 86400


class TaskTracker:
    """
    Redis-based task tracker with permission-aware access control.

    Stores task metadata in Redis with permission tags, enabling:
    - Users to see their own tasks
    - Course lecturers+ to see tasks related to their courses
    - Organization admins to see tasks in their organizations
    - System admins to see all tasks

    Redis key structure:
    - task:{workflow_id} -> TaskTrackerEntry JSON
    - task_idx:user:{user_id} -> Set of workflow_ids
    - task_idx:course:{course_id} -> Set of workflow_ids
    - task_idx:org:{organization_id} -> Set of workflow_ids
    - task_idx:all -> Set of all workflow_ids (for admin listing)
    """

    def __init__(self, redis_client: aioredis.Redis):
        """
        Initialize TaskTracker.

        Args:
            redis_client: Async Redis client instance
        """
        self.redis = redis_client

    def _key(self, *parts: str) -> str:
        """Build a key from parts."""
        return ":".join(str(p) for p in parts)

    async def track_task(
        self,
        workflow_id: str,
        task_name: str,
        created_by: str,
        user_id: Optional[str] = None,
        course_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        description: Optional[str] = None,
        ttl: int = DEFAULT_TASK_TTL
    ) -> TaskTrackerEntry:
        """
        Track a new task in Redis with permission tags.

        Args:
            workflow_id: Temporal workflow ID
            task_name: Name of the task/workflow
            created_by: User ID who submitted the task
            user_id: User context for permission (defaults to created_by)
            course_id: Course context for permission
            organization_id: Organization context for permission
            entity_type: Type of entity this task relates to
            entity_id: ID of the entity
            description: Human-readable description
            ttl: Time-to-live in seconds (default 24 hours)

        Returns:
            TaskTrackerEntry with all metadata
        """
        entry = TaskTrackerEntry(
            workflow_id=workflow_id,
            task_name=task_name,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
            user_id=user_id or created_by,
            course_id=course_id,
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description
        )

        try:
            pipe = self.redis.pipeline()

            # Store the task entry
            task_key = self._key("task", workflow_id)
            pipe.setex(task_key, ttl, entry.model_dump_json())

            # Add to indexes for efficient querying
            # User index - always add (user can see their own tasks)
            user_index_key = self._key("task_idx", "user", entry.user_id)
            pipe.sadd(user_index_key, workflow_id)
            pipe.expire(user_index_key, ttl)

            # Course index - if course_id provided
            if course_id:
                course_index_key = self._key("task_idx", "course", course_id)
                pipe.sadd(course_index_key, workflow_id)
                pipe.expire(course_index_key, ttl)

            # Organization index - if organization_id provided
            if organization_id:
                org_index_key = self._key("task_idx", "org", organization_id)
                pipe.sadd(org_index_key, workflow_id)
                pipe.expire(org_index_key, ttl)

            # Global index for admin listing
            all_index_key = self._key("task_idx", "all")
            pipe.sadd(all_index_key, workflow_id)
            pipe.expire(all_index_key, ttl)

            await pipe.execute()
            logger.info(f"Tracked task {workflow_id} for user {created_by}")

            return entry

        except Exception as e:
            logger.error(f"Failed to track task {workflow_id}: {e}")
            raise

    async def get_task_entry(self, workflow_id: str) -> Optional[TaskTrackerEntry]:
        """
        Get task entry by workflow ID.

        Args:
            workflow_id: Temporal workflow ID

        Returns:
            TaskTrackerEntry or None if not found
        """
        try:
            task_key = self._key("task", workflow_id)
            data = await self.redis.get(task_key)

            if data:
                return TaskTrackerEntry.model_validate_json(data)
            return None

        except Exception as e:
            logger.error(f"Failed to get task entry {workflow_id}: {e}")
            return None

    async def can_access_task(
        self,
        workflow_id: str,
        permissions: Principal
    ) -> bool:
        """
        Check if user has permission to access a task.

        Access is granted if:
        - User is admin
        - User created the task (user_id matches)
        - User has _lecturer+ role in the task's course
        - User has org-level admin role for the task's organization

        Args:
            workflow_id: Temporal workflow ID
            permissions: User's principal with roles

        Returns:
            True if user can access the task
        """
        # Admin can access everything
        if permissions.is_admin:
            return True

        entry = await self.get_task_entry(workflow_id)
        if not entry:
            return False

        # User can access their own tasks
        if entry.user_id == permissions.user_id:
            return True

        # Check course-level access (lecturer+)
        if entry.course_id:
            user_role = permissions.get_highest_course_role(entry.course_id)
            if user_role:
                role_level = course_role_hierarchy.get_role_level(user_role)
                lecturer_level = course_role_hierarchy.get_role_level("_lecturer")
                if role_level >= lecturer_level:
                    return True

        # TODO: Add organization-level access check when org roles are implemented

        return False

    async def list_accessible_tasks(
        self,
        permissions: Principal,
        limit: int = 100,
        offset: int = 0
    ) -> List[TaskTrackerEntry]:
        """
        List tasks the user has access to.

        Args:
            permissions: User's principal with roles
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip

        Returns:
            List of TaskTrackerEntry objects
        """
        try:
            workflow_ids = set()

            if permissions.is_admin:
                # Admin sees all tasks
                all_index_key = self._key("task_idx", "all")
                all_ids = await self.redis.smembers(all_index_key)
                workflow_ids.update(all_ids)
            else:
                # User's own tasks
                user_index_key = self._key("task_idx", "user", permissions.user_id)
                user_ids = await self.redis.smembers(user_index_key)
                workflow_ids.update(user_ids)

                # Tasks from courses where user is lecturer+
                for course_id, role in permissions.course_roles.items():
                    role_level = course_role_hierarchy.get_role_level(role)
                    lecturer_level = course_role_hierarchy.get_role_level("_lecturer")
                    if role_level >= lecturer_level:
                        course_index_key = self._key("task_idx", "course", course_id)
                        course_ids = await self.redis.smembers(course_index_key)
                        workflow_ids.update(course_ids)

            # Fetch task entries
            entries = []
            for wf_id in workflow_ids:
                entry = await self.get_task_entry(wf_id)
                if entry:
                    entries.append(entry)

            # Sort by created_at descending (newest first)
            entries.sort(key=lambda e: e.created_at, reverse=True)

            # Apply pagination
            return entries[offset:offset + limit]

        except Exception as e:
            logger.error(f"Failed to list accessible tasks: {e}")
            return []

    async def get_accessible_task_ids(
        self,
        permissions: Principal
    ) -> set:
        """
        Get set of workflow IDs the user can access.

        Args:
            permissions: User's principal with roles

        Returns:
            Set of workflow IDs
        """
        try:
            workflow_ids = set()

            if permissions.is_admin:
                all_index_key = self._key("task_idx", "all")
                all_ids = await self.redis.smembers(all_index_key)
                workflow_ids.update(all_ids)
            else:
                # User's own tasks
                user_index_key = self._key("task_idx", "user", permissions.user_id)
                user_ids = await self.redis.smembers(user_index_key)
                workflow_ids.update(user_ids)

                # Tasks from courses where user is lecturer+
                for course_id, role in permissions.course_roles.items():
                    role_level = course_role_hierarchy.get_role_level(role)
                    lecturer_level = course_role_hierarchy.get_role_level("_lecturer")
                    if role_level >= lecturer_level:
                        course_index_key = self._key("task_idx", "course", course_id)
                        course_ids = await self.redis.smembers(course_index_key)
                        workflow_ids.update(course_ids)

            return workflow_ids

        except Exception as e:
            logger.error(f"Failed to get accessible task IDs: {e}")
            return set()

    async def submit_and_track_task(
        self,
        task_submission,  # TaskSubmission from computor_types
        created_by: str,
        user_id: Optional[str] = None,
        course_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        description: Optional[str] = None,
        ttl: int = DEFAULT_TASK_TTL
    ) -> str:
        """
        Submit a task to Temporal and track it in Redis in one operation.

        This is the recommended way to submit tasks when permission tracking is needed.

        Args:
            task_submission: TaskSubmission object with task details
            created_by: User ID who submitted the task
            user_id: User context for permission (defaults to created_by)
            course_id: Course context for permission
            organization_id: Organization context for permission
            entity_type: Type of entity this task relates to
            entity_id: ID of the entity
            description: Human-readable description
            ttl: Time-to-live in seconds (default 24 hours)

        Returns:
            workflow_id of the submitted task
        """
        from computor_backend.tasks import get_task_executor

        task_executor = get_task_executor()
        workflow_id = await task_executor.submit_task(task_submission)

        # Track the task in Redis
        await self.track_task(
            workflow_id=workflow_id,
            task_name=task_submission.task_name,
            created_by=created_by,
            user_id=user_id,
            course_id=course_id,
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ttl=ttl
        )

        return workflow_id

    async def delete_task_entry(self, workflow_id: str) -> bool:
        """
        Delete a task entry from Redis.

        Args:
            workflow_id: Temporal workflow ID

        Returns:
            True if deleted successfully
        """
        try:
            entry = await self.get_task_entry(workflow_id)
            if not entry:
                return False

            pipe = self.redis.pipeline()

            # Remove from indexes
            pipe.srem(self._key("task_idx", "user", entry.user_id), workflow_id)
            if entry.course_id:
                pipe.srem(self._key("task_idx", "course", entry.course_id), workflow_id)
            if entry.organization_id:
                pipe.srem(self._key("task_idx", "org", entry.organization_id), workflow_id)
            pipe.srem(self._key("task_idx", "all"), workflow_id)

            # Remove the task entry itself
            pipe.delete(self._key("task", workflow_id))

            await pipe.execute()
            logger.info(f"Deleted task entry {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete task entry {workflow_id}: {e}")
            return False


# Global task tracker instance (initialized lazily)
_task_tracker: Optional[TaskTracker] = None


async def get_task_tracker() -> TaskTracker:
    """
    Get the global TaskTracker instance.

    Returns:
        TaskTracker instance
    """
    global _task_tracker

    if _task_tracker is None:
        from computor_backend.redis_cache import get_redis_client
        redis_client = await get_redis_client()
        _task_tracker = TaskTracker(redis_client)

    return _task_tracker


def reset_task_tracker() -> None:
    """Reset the global TaskTracker instance (for testing)."""
    global _task_tracker
    _task_tracker = None
