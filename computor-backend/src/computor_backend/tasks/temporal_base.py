"""
Base classes and interfaces for Temporal workflow and activity definitions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional
from temporalio.common import RetryPolicy


@dataclass
class WorkflowResult:
    """Standard result structure for workflows."""
    status: str
    result: Any
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseWorkflow(ABC):
    """
    Abstract base class for Temporal workflows.

    Workflows orchestrate the execution of activities and handle long-running processes.
    """

    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Get the workflow name."""
        pass

    @classmethod
    def get_task_queue(cls) -> str:
        """Get the default task queue for this workflow."""
        return "computor-tasks"

    @classmethod
    def get_execution_timeout(cls) -> timedelta:
        """Get the workflow execution timeout."""
        return timedelta(hours=1)

    @classmethod
    def get_retry_policy(cls) -> RetryPolicy:
        """Get the retry policy for this workflow."""
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=100),
            maximum_attempts=3,
        )