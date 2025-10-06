"""
Base classes and interfaces for Temporal workflow and activity definitions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional, List
from temporalio import workflow, activity
from temporalio.common import RetryPolicy

from .base import TaskStatus, TaskSubmission


@dataclass
class WorkflowProgress:
    """Progress information for workflow execution."""
    percentage: int
    stage: str
    metadata: Optional[Dict[str, Any]] = None


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


class BaseActivity(ABC):
    """
    Abstract base class for Temporal activities.
    
    Activities contain the actual business logic and can interact with external systems.
    """
    
    @classmethod
    @abstractmethod
    def get_name(cls) -> str:
        """Get the activity name."""
        pass
    
    @classmethod
    def get_start_to_close_timeout(cls) -> timedelta:
        """Get the activity execution timeout."""
        return timedelta(minutes=5)
    
    @classmethod
    def get_retry_policy(cls) -> RetryPolicy:
        """Get the retry policy for this activity."""
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=100),
            maximum_attempts=3,
        )
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the activity logic.
        
        Args:
            **kwargs: Activity parameters
            
        Returns:
            Activity result
        """
        pass


def create_activity_decorator(activity_class: type[BaseActivity]):
    """
    Create a Temporal activity decorator for a BaseActivity class.
    
    This helper function creates properly configured Temporal activities
    from our BaseActivity classes.
    """
    @activity.defn(name=activity_class.get_name())
    async def activity_wrapper(**kwargs):
        instance = activity_class()
        return await instance.execute(**kwargs)
    
    return activity_wrapper


def create_workflow_decorator(workflow_class: type[BaseWorkflow]):
    """
    Create a Temporal workflow decorator for a BaseWorkflow class.
    
    This helper function creates properly configured Temporal workflows
    from our BaseWorkflow classes.
    """
    def decorator(run_method):
        return workflow.defn(
            name=workflow_class.get_name(),
            sandboxed=False  # Python workflows can't be sandboxed
        )(run_method)
    
    return decorator