"""
Computor Framework - Dependencies Module

Provides tools for managing and installing dependencies across
Python, R, Octave, and system packages.
"""

from .models import (
    Dependencies,
    PythonDependencies,
    PythonPackage,
    RDependencies,
    RPackage,
    OctaveDependencies,
    OctavePackage,
    SystemDependencies,
)

__all__ = [
    "Dependencies",
    "PythonDependencies",
    "PythonPackage",
    "RDependencies",
    "RPackage",
    "OctaveDependencies",
    "OctavePackage",
    "SystemDependencies",
]
