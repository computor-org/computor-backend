"""DEPRECATED module path — renamed to ``computor_types.test_jobs`` (TASK-511).

The name ``tests`` collided (mentally and in tab-completion) with actual
test directories and pytest conventions. Import from
``computor_types.test_jobs`` instead. This shim re-exports the public names
so existing and generated imports keep working; remove after one release.
"""
from computor_types.test_jobs import TestJob, TestCreate  # noqa: F401

__all__ = ["TestJob", "TestCreate"]
