"""
Testing module for student code evaluation.
Provides flexible backend system for different programming languages and testing frameworks.
"""

from .backends import (
    TestingBackend,
    UnifiedTestingBackend,
    PythonTestingBackend,
    MatlabTestingBackend,
    JavaTestingBackend,
    TestingBackendFactory,
    execute_tests_with_backend
)

__all__ = [
    "TestingBackend",
    "UnifiedTestingBackend",
    "PythonTestingBackend",
    "MatlabTestingBackend",
    "JavaTestingBackend",
    "TestingBackendFactory",
    "execute_tests_with_backend"
]