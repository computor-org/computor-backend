"""
Lightweight event publisher for broadcasting WebSocket events via Redis.

Designed for use from Temporal activities, background tasks, and other
non-API contexts that don't have access to the WebSocket ConnectionManager
or async event loop.

Uses synchronous Redis publish — safe to call from Temporal activities
which run in a sync context (activity.defn(sandboxed=False)).

Usage from a Temporal activity:
    from computor_backend.websocket.event_publisher import publish_deployment_status_changed

    publish_deployment_status_changed(
        course_id="...",
        course_content_id="...",
        deployment_id="...",
        previous_status="deploying",
        new_status="deployed",
    )

Usage from async API context (prefer WebSocketBroadcast instead):
    from computor_backend.websocket.event_publisher import publish_deployment_status_changed

    # Also works from async, but ws_broadcast methods are preferred in API layer
    publish_deployment_status_changed(...)
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import redis

from computor_backend.websocket.pubsub import CHANNEL_PREFIX

logger = logging.getLogger(__name__)

# Lazy-initialized sync Redis client
_sync_redis: Optional[redis.Redis] = None


def _get_sync_redis() -> redis.Redis:
    """Get or create a sync Redis client for publishing events."""
    global _sync_redis
    if _sync_redis is None:
        _sync_redis = redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=int(os.environ.get('REDIS_PORT', '6379')),
            password=os.environ.get('REDIS_PASSWORD', '') or None,
            db=int(os.environ.get('REDIS_DB', '0')),
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
    return _sync_redis


def _publish_event(channel: str, event_type: str, data: dict) -> None:
    """
    Publish a WebSocket event to Redis pub/sub.

    This is the low-level publish function. Use the typed helpers below.

    Args:
        channel: Logical channel name (e.g., "course:uuid")
        event_type: Event type string (e.g., "deployment:status_changed")
        data: Event payload dict
    """
    try:
        client = _get_sync_redis()
        full_channel = f"{CHANNEL_PREFIX}{channel}"
        message = json.dumps({
            "type": event_type,
            "channel": channel,
            "data": data,
        })
        client.publish(full_channel, message)
        logger.debug(f"Published {event_type} to {full_channel}")
    except Exception as e:
        # Never let a broadcast failure break the caller's workflow
        logger.error(f"Failed to publish {event_type} to {channel}: {e}")


def _invalidate_cache_tags(*tags: str) -> None:
    """
    Invalidate cache tags before broadcasting.

    Uses the sync Cache instance so HTTP re-fetches triggered by
    the WebSocket event will get fresh data.
    """
    try:
        from computor_backend.redis_cache import get_cache
        cache = get_cache()
        cache.invalidate_tags(*tags)
    except Exception as e:
        logger.warning(f"Cache invalidation failed for tags {tags}: {e}")


def _now_iso() -> str:
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


# =========================================================================
# Typed publish helpers
# =========================================================================

def publish_deployment_status_changed(
    course_id: str,
    course_content_id: str,
    deployment_id: str,
    previous_status: str,
    new_status: str,
    version_tag: Optional[str] = None,
    example_identifier: Optional[str] = None,
    deployment_message: Optional[str] = None,
    deployed_at: Optional[str] = None,
    workflow_id: Optional[str] = None,
) -> None:
    """
    Broadcast a deployment status change event.

    Call AFTER db.commit() succeeds. Invalidates cache before publishing.

    Args:
        course_id: Course UUID string
        course_content_id: CourseContent UUID string
        deployment_id: CourseContentDeployment UUID string
        previous_status: Status before the transition
        new_status: Status after the transition
        version_tag: Semantic version tag (e.g., "1.0.0")
        example_identifier: Ltree example identifier
        deployment_message: Error or status message
        deployed_at: ISO8601 timestamp of deployment completion
        workflow_id: Temporal workflow ID
    """
    _invalidate_cache_tags(
        f"course_id:{course_id}",
        f"course_content:{course_content_id}",
        f"course_content_deployment:{deployment_id}",
    )

    channel = f"course:{course_id}"
    _publish_event(channel, "deployment:status_changed", {
        "channel": channel,
        "course_id": course_id,
        "course_content_id": course_content_id,
        "deployment_id": deployment_id,
        "previous_status": previous_status,
        "new_status": new_status,
        "version_tag": version_tag,
        "example_identifier": example_identifier,
        "deployment_message": deployment_message,
        "deployed_at": deployed_at,
        "workflow_id": workflow_id,
        "timestamp": _now_iso(),
    })


def publish_deployment_assigned(
    course_id: str,
    course_content_id: str,
    deployment_id: str,
    version_tag: str,
    deployment_status: str,
    example_identifier: Optional[str] = None,
) -> None:
    """
    Broadcast a deployment assignment event.

    Call AFTER db.commit() succeeds.

    Args:
        course_id: Course UUID string
        course_content_id: CourseContent UUID string
        deployment_id: CourseContentDeployment UUID string
        version_tag: Semantic version tag
        deployment_status: Current status (typically "pending")
        example_identifier: Ltree example identifier
    """
    _invalidate_cache_tags(
        f"course_id:{course_id}",
        f"course_content:{course_content_id}",
        f"course_content_deployment:{deployment_id}",
    )

    channel = f"course:{course_id}"
    _publish_event(channel, "deployment:assigned", {
        "channel": channel,
        "course_id": course_id,
        "course_content_id": course_content_id,
        "deployment_id": deployment_id,
        "example_identifier": example_identifier,
        "version_tag": version_tag,
        "deployment_status": deployment_status,
        "timestamp": _now_iso(),
    })


def publish_deployment_unassigned(
    course_id: str,
    course_content_id: str,
    previous_example_identifier: Optional[str] = None,
    previous_version_tag: Optional[str] = None,
) -> None:
    """
    Broadcast a deployment unassignment event.

    Call AFTER db.commit() succeeds.

    Args:
        course_id: Course UUID string
        course_content_id: CourseContent UUID string
        previous_example_identifier: Previously assigned example identifier
        previous_version_tag: Previously assigned version tag
    """
    _invalidate_cache_tags(
        f"course_id:{course_id}",
        f"course_content:{course_content_id}",
    )

    channel = f"course:{course_id}"
    _publish_event(channel, "deployment:unassigned", {
        "channel": channel,
        "course_id": course_id,
        "course_content_id": course_content_id,
        "previous_example_identifier": previous_example_identifier,
        "previous_version_tag": previous_version_tag,
        "timestamp": _now_iso(),
    })


def publish_course_content_updated(
    course_id: str,
    course_content_id: str,
    change_type: str,
) -> None:
    """
    Broadcast a course content mutation event.

    Call AFTER db.commit() succeeds.

    Args:
        course_id: Course UUID string
        course_content_id: CourseContent UUID string
        change_type: One of "created", "updated", "deleted", "reordered"
    """
    _invalidate_cache_tags(
        f"course_id:{course_id}",
        f"course_content:{course_content_id}",
    )

    channel = f"course:{course_id}"
    _publish_event(channel, "course:content_updated", {
        "channel": channel,
        "course_id": course_id,
        "course_content_id": course_content_id,
        "change_type": change_type,
        "timestamp": _now_iso(),
    })
