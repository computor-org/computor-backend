"""
Testing module for student code evaluation.
Provides flexible backend system for different programming languages and testing frameworks.
"""

from .backends import (
    TestingBackend,
    ComputorTestingBackend,
    PythonTestingBackend,
    MatlabTestingBackend,
    JavaTestingBackend,
    TestingBackendFactory,
    execute_tests_with_backend
)

__all__ = [
    "TestingBackend",
    "ComputorTestingBackend",
    "PythonTestingBackend",
    "MatlabTestingBackend",
    "JavaTestingBackend",
    "TestingBackendFactory",
    "execute_tests_with_backend"
]