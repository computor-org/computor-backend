"""
Task execution framework for long-running operations.

This module provides a Temporal-based task execution system
that handles operations exceeding FastAPI's request-response cycle.
"""

from .temporal_executor import TemporalTaskExecutor as TaskExecutor, get_task_executor
from .registry import (
    task_registry,
    register_task,
    import_task_modules,
    TEMPORAL_TASK_MODULES,
)
from computor_types.tasks import TaskResult, TaskSubmission, TaskInfo, TaskStatus
from .temporal_client import (
    get_temporal_client,
    close_temporal_client,
    get_task_queue_name,
    DEFAULT_TASK_QUEUE
)
from .temporal_base import BaseWorkflow, WorkflowResult

# Import every Temporal task module so its workflows/activities auto-register
# and become submittable through the public task API. This is the single place
# the module list lives (TEMPORAL_TASK_MODULES in registry.py). Demo/example
# workflows are only imported when COMPUTOR_ENABLE_EXAMPLE_TASKS=1, so nobody
# can launch an arbitrary long-running job in production.
import_task_modules()

__all__ = [
    'TaskExecutor',
    'get_task_executor', 
    'TaskStatus',
    'TaskResult',
    'TaskSubmission',
    'TaskInfo',
    'task_registry',
    'register_task',
    'import_task_modules',
    'TEMPORAL_TASK_MODULES',
    'get_temporal_client',
    'close_temporal_client',
    'get_task_queue_name',
    'DEFAULT_TASK_QUEUE',
    'BaseWorkflow',
    'WorkflowResult',
]
