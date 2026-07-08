"""
Task registry for managing and discovering workflow implementations.

This is the single source of truth for which Temporal task modules exist
(``TEMPORAL_TASK_MODULES``) and for the set of workflow classes / activity
functions the worker registers. Both ``tasks/__init__.py`` (public task API
auto-registration) and ``tasks/temporal_worker.py`` (worker registration)
import from here, so adding a new module only requires editing the
``TEMPORAL_TASK_MODULES`` list below.
"""

import importlib
import os
import sys
from typing import Callable, Dict, List, Type


# Single source of truth for the Temporal task modules. Adding a new module
# means adding it here (and giving it ``@register_task`` classes + an
# ``ACTIVITIES`` list) — nothing else needs to change.
#
# Order mirrors the historical ``_TEMPORAL_MODULES`` order so the derived
# workflow/activity registration order is unchanged.
TEMPORAL_TASK_MODULES: List[str] = [
    ".temporal_student_testing",
    ".temporal_hierarchy_management",
    ".temporal_student_template_v2",
    ".temporal_assignments_repository",
    ".temporal_student_repository",
    ".temporal_tutor_testing",
    ".temporal_coder_setup",
]

# Demo/example workflows are only imported (and therefore only registered /
# submittable) when explicitly enabled, so nobody can launch an arbitrary
# long-running job in production.
EXAMPLE_TASK_MODULES: List[str] = [
    ".temporal_examples",
]

_PACKAGE = "computor_backend.tasks"


class TaskRegistry:
    """Registry for managing workflow implementations and their activities."""

    def __init__(self):
        self._tasks: Dict[str, Type] = {}
        # Insertion-ordered unique set of module names that registered a
        # workflow. Used to derive the activity set (each module declares its
        # activities in a module-level ``ACTIVITIES`` list).
        self._modules: Dict[str, None] = {}

    def register(self, task_class: Type) -> Type:
        """
        Register a workflow implementation.

        Also records the defining module so the worker can derive that
        module's activities from the registry (see ``list_activities``).

        Args:
            task_class: Workflow class to register (must have get_name classmethod)

        Returns:
            The registered class (for decorator usage)
        """
        task_name = task_class.get_name()

        if task_name in self._tasks:
            raise ValueError(f"Task '{task_name}' is already registered")

        self._tasks[task_name] = task_class
        self._modules.setdefault(task_class.__module__, None)
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

    def list_workflows(self) -> List[Type]:
        """All registered workflow classes, in registration order."""
        return list(self._tasks.values())

    def list_activities(self) -> List[Callable]:
        """
        All activity functions the worker should register, derived from the
        ``ACTIVITIES`` list of every module that registered a workflow.

        De-duplicated by function identity while preserving order.
        """
        activities: List[Callable] = []
        seen = set()
        for module_name in self._modules:
            module = sys.modules.get(module_name)
            for activity_fn in getattr(module, "ACTIVITIES", []) or []:
                if activity_fn not in seen:
                    seen.add(activity_fn)
                    activities.append(activity_fn)
        return activities


# Global task registry instance
task_registry = TaskRegistry()


def register_task(task_class: Type) -> Type:
    """Decorator for registering workflow implementations."""
    return task_registry.register(task_class)


def iter_task_module_names(include_examples: bool = None) -> List[str]:
    """The task module names to import, honouring the example-tasks env flag."""
    if include_examples is None:
        include_examples = os.environ.get("COMPUTOR_ENABLE_EXAMPLE_TASKS") == "1"
    names = list(TEMPORAL_TASK_MODULES)
    if include_examples:
        names.extend(EXAMPLE_TASK_MODULES)
    return names


def import_task_modules(include_examples: bool = None) -> List:
    """
    Import every Temporal task module so its workflows/activities register.

    Idempotent: modules already imported are returned from the module cache
    without re-running their ``@register_task`` decorators.

    Returns the imported module objects (in import order).
    """
    modules = []
    for name in iter_task_module_names(include_examples):
        modules.append(importlib.import_module(name, _PACKAGE))
    return modules
