from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class TaskStatus(str, Enum):
    """Task execution status enumeration."""
    QUEUED = "queued"
    STARTED = "started"
    FINISHED = "finished"
    FAILED = "failed"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"

def map_task_status_to_int(status: TaskStatus) -> int:
    """Map TaskStatus enum to legacy integer for database storage."""
    mapping = {
        TaskStatus.FINISHED: 0,    # FINISHED -> COMPLETED (0)
        TaskStatus.FAILED: 1,      # FAILED -> FAILED (1)
        TaskStatus.CANCELLED: 2,   # CANCELLED -> CANCELLED (2)
        TaskStatus.QUEUED: 4,      # QUEUED -> PENDING (4)
        TaskStatus.STARTED: 5,     # STARTED -> RUNNING (5)
        TaskStatus.DEFERRED: 7     # DEFERRED -> PAUSED (7)
    }
    return mapping.get(status, 1)  # Default to FAILED (1)

def map_int_to_task_status(value: int | str | TaskStatus | None) -> TaskStatus:
    """Map legacy status representations (ints/strings) to TaskStatus."""
    if value is None:
        return TaskStatus.FAILED

    if isinstance(value, TaskStatus):
        return value

    if isinstance(value, str):
        try:
            return TaskStatus(value)
        except ValueError:
            try:
                return TaskStatus(value.lower())
            except ValueError:
                return TaskStatus.FAILED

    mapping = {
        0: TaskStatus.FINISHED,   # COMPLETED
        1: TaskStatus.FAILED,     # FAILED
        2: TaskStatus.CANCELLED,  # CANCELLED
        3: TaskStatus.QUEUED,     # SCHEDULED
        4: TaskStatus.QUEUED,     # PENDING
        5: TaskStatus.STARTED,    # RUNNING
        6: TaskStatus.FAILED,     # CRASHED (treat as failed)
        7: TaskStatus.DEFERRED,   # PAUSED
    }
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        return TaskStatus.FAILED
    return mapping.get(int_value, TaskStatus.FAILED)


# Task DTOs for API endpoints

class TaskResult(BaseModel):
    """Task execution result container."""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    progress: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(use_enum_values=True, arbitrary_types_allowed=True)


class TaskSubmission(BaseModel):
    """Task submission request."""
    task_name: str
    parameters: Dict[str, Any] = {}
    queue: str = "computor-tasks"  # Task queue name
    workflow_id: Optional[str] = None  # Custom workflow ID (if not provided, will be auto-generated)
    delay: Optional[int] = None  # Delay in seconds before execution


class TaskInfo(BaseModel):
    """Task information for status queries."""
    task_id: str
    task_name: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    progress: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    worker: Optional[str] = None
    queue: Optional[str] = None
    retries: Optional[int] = None
    args: Optional[Any] = None
    kwargs: Optional[Dict[str, Any]] = None

    # UI enhancement fields
    short_task_id: Optional[str] = None
    status_display: Optional[str] = None
    completed_at: Optional[datetime] = None
    has_result: Optional[bool] = None
    result_available: Optional[str] = None
    duration: Optional[str] = None
    workflow_id: Optional[str] = None
    run_id: Optional[str] = None
    execution_time: Optional[datetime] = None
    history_length: Optional[int] = None

    model_config = ConfigDict(use_enum_values=True, arbitrary_types_allowed=True)


class TaskTrackerEntry(BaseModel):
    """
    Task tracking entry stored in Redis for permission-aware task access.

    This model stores permission-relevant metadata about tasks, allowing
    non-admin users to query tasks they have access to.
    """
    workflow_id: str
    task_name: str
    created_at: datetime
    created_by: str  # user_id of who submitted the task

    # Permission context tags - used to determine access
    user_id: Optional[str] = None  # User context (can see own tasks)
    course_id: Optional[str] = None  # Course context (lecturers+ can see)
    organization_id: Optional[str] = None  # Org context (org admins can see)

    # Additional context
    entity_type: Optional[str] = None  # e.g., "course_member", "deployment"
    entity_id: Optional[str] = None  # Specific entity ID
    description: Optional[str] = None  # Human-readable description

    model_config = ConfigDict(use_enum_values=True, arbitrary_types_allowed=True)
