"""
Task execution framework for long-running operations.

This module provides a Temporal-based task execution system
that handles operations exceeding FastAPI's request-response cycle.
"""

from .temporal_executor import TemporalTaskExecutor as TaskExecutor, get_task_executor
from .base import BaseTask
from .registry import task_registry, register_task
from computor_types.tasks import TaskResult, TaskSubmission, TaskInfo, TaskStatus
from .temporal_client import (
    get_temporal_client, 
    close_temporal_client,
    get_task_queue_name,
    DEFAULT_TASK_QUEUE
)
from .temporal_base import BaseWorkflow, BaseActivity, WorkflowResult, WorkflowProgress

# Import Temporal examples to auto-register tasks
from . import temporal_examples

# Import Temporal hierarchy management tasks to auto-register
from . import temporal_hierarchy_management

# Import Temporal student testing tasks to auto-register
from . import temporal_student_testing

# Import Temporal student template tasks to auto-register
from . import temporal_student_template_v2

# Import Temporal student repository tasks to auto-register
from . import temporal_student_repository

# Import Assignments repository tasks to auto-register
from . import temporal_assignments_repository

# Import Documents sync tasks to auto-register
from . import temporal_documents_sync

# Import Tutor testing tasks to auto-register
from . import temporal_tutor_testing

# Import Coder setup tasks to auto-register (image building, template push)
from . import temporal_coder_setup

__all__ = [
    'TaskExecutor',
    'get_task_executor', 
    'BaseTask',
    'TaskStatus',
    'TaskResult',
    'TaskSubmission',
    'TaskInfo',
    'task_registry',
    'register_task',
    'get_temporal_client',
    'close_temporal_client',
    'get_task_queue_name',
    'DEFAULT_TASK_QUEUE',
    'BaseWorkflow',
    'BaseActivity',
    'WorkflowResult',
    'WorkflowProgress'
]
