"""
Base classes and interfaces for task execution framework.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from computor_types.tasks import TaskStatus, TaskResult, TaskSubmission, TaskInfo


class BaseTask(ABC):
    """
    Abstract base class for all task implementations.
    
    Tasks should inherit from this class and implement the execute method.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifier for this task type."""
        pass
    
    @property
    def timeout(self) -> Optional[int]:
        """Task timeout in seconds. None for no timeout."""
        return 3600  # 1 hour default
    
    @property
    def retry_limit(self) -> int:
        """Maximum number of retry attempts."""
        return 3
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """
        Execute the task with given parameters.
        
        Args:
            **kwargs: Task parameters
            
        Returns:
            Task execution result
            
        Raises:
            Exception: If task execution fails
        """
        pass
    
    async def on_success(self, result: Any, **kwargs) -> None:
        """
        Hook called when task completes successfully.
        
        Args:
            result: Task execution result
            **kwargs: Original task parameters
        """
        pass
    
    async def on_failure(self, error: Exception, **kwargs) -> None:
        """
        Hook called when task fails.
        
        Args:
            error: Exception that caused the failure
            **kwargs: Original task parameters
        """
        pass
    
    async def update_progress(self, percentage: int, metadata: Dict[str, Any] = None) -> None:
        """
        Update task progress.
        
        This method should be called during task execution to report progress.
        The implementation depends on how the task is being executed (Celery, etc.).
        
        Args:
            percentage: Progress percentage (0-100)
            metadata: Additional progress metadata
        """
        # Default implementation does nothing
        # This will be overridden by the Celery wrapper in executor.py
        pass