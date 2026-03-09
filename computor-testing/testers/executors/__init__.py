"""
Language Executors

All language-specific executors in one place.
Each executor inherits from ctexec base classes.
"""

from .python import PyExecutor, check_python_installed
from .octave import OctaveExecutor, check_octave_installed
from .r import RExecutor, check_r_installed
from .julia import JuliaExecutor, check_julia_installed
from .c import CExecutor, check_c_installed
from .fortran import FortranExecutor, check_fortran_installed
from .document import DocumentAnalyzer

# Registry mapping language -> executor class
EXECUTORS = {
    "python": PyExecutor,
    "octave": OctaveExecutor,
    "r": RExecutor,
    "julia": JuliaExecutor,
    "c": CExecutor,
    "fortran": FortranExecutor,
    "document": DocumentAnalyzer,
}


def get_executor(language: str):
    """
    Get the executor class for a language.

    Args:
        language: Language identifier

    Returns:
        Executor class or None if not found
    """
    return EXECUTORS.get(language.lower())


__all__ = [
    # Executors
    "PyExecutor",
    "OctaveExecutor",
    "RExecutor",
    "JuliaExecutor",
    "CExecutor",
    "FortranExecutor",
    "DocumentAnalyzer",
    # Check functions
    "check_python_installed",
    "check_octave_installed",
    "check_r_installed",
    "check_julia_installed",
    "check_c_installed",
    "check_fortran_installed",
    # Registry
    "EXECUTORS",
    "get_executor",
]
