from enum import Enum

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
