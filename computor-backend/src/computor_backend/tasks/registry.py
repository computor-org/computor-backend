"""
Task registry for managing and discovering workflow implementations.
"""

from typing import Dict, Type


class TaskRegistry:
    """Registry for managing workflow implementations."""

    def __init__(self):
        self._tasks: Dict[str, Type] = {}

    def register(self, task_class: Type) -> Type:
        """
        Register a workflow implementation.

        Args:
            task_class: Workflow class to register (must have get_name classmethod)

        Returns:
            The registered class (for decorator usage)
        """
        task_name = task_class.get_name()

        if task_name in self._tasks:
            raise ValueError(f"Task '{task_name}' is already registered")

        self._tasks[task_name] = task_class
        return task_class

    def get_task(self, task_name: str) -> Type:
        """Get a workflow implementation by name."""
        if task_name not in self._tasks:
            raise KeyError(f"Task '{task_name}' is not registered")
        return self._tasks[task_name]

    def list_tasks(self) -> Dict[str, Type]:
        """Get all registered workflows."""
        return self._tasks.copy()

    def is_registered(self, task_name: str) -> bool:
        """Check if a workflow is registered."""
        return task_name in self._tasks


# Global task registry instance
task_registry = TaskRegistry()


def register_task(task_class: Type) -> Type:
    """Decorator for registering workflow implementations."""
    return task_registry.register(task_class)
