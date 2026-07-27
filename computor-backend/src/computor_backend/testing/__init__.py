"""
Testing module for student code evaluation.
Provides flexible backend system for different programming languages and testing frameworks.

Backends are selected by ``Service.config.language``, never by service slug —
see ``TestingBackendFactory``.
"""

from .backends import (
    TestingBackend,
    ComputorTestingBackend,
    MatlabTestingBackend,
    TestingBackendFactory,
    execute_tests_with_backend
)

__all__ = [
    "TestingBackend",
    "ComputorTestingBackend",
    "MatlabTestingBackend",
    "TestingBackendFactory",
    "execute_tests_with_backend"
]
