"""
Computor Testing Framework - Language Testers

Unified testing infrastructure for all supported languages.

Supported languages:
- Python (pytester)
- Octave/MATLAB (octester)
- R (rtester)
- Julia (jltester)
- C/C++ (ctester)
- Fortran (ftester)
- Document analysis (doctester)

Usage:
    from testers import get_tester, list_testers

    # Get a specific tester
    tester = get_tester("python")

    # Run tests
    tester.run(target="student_code/", testsuite="test.yaml")
"""

from typing import Dict, List, Optional, Type

# Language registry
LANGUAGES: Dict[str, str] = {
    "python": "Python",
    "py": "Python",
    "octave": "GNU Octave",
    "matlab": "GNU Octave",
    "oct": "GNU Octave",
    "r": "R",
    "julia": "Julia",
    "jl": "Julia",
    "c": "C/C++",
    "cpp": "C/C++",
    "c++": "C/C++",
    "fortran": "Fortran",
    "f90": "Fortran",
    "f95": "Fortran",
    "document": "Document Analysis",
    "doc": "Document Analysis",
}


def list_testers() -> List[str]:
    """
    List all available tester languages.

    Returns:
        List of canonical language names
    """
    return ["python", "octave", "r", "julia", "c", "fortran", "document"]


def get_language_name(language: str) -> Optional[str]:
    """
    Get the human-readable name for a language.

    Args:
        language: Language identifier (e.g., "python", "py", "octave")

    Returns:
        Human-readable name or None if not found
    """
    return LANGUAGES.get(language.lower())


def normalize_language(language: str) -> Optional[str]:
    """
    Normalize a language identifier to its canonical form.

    Args:
        language: Language identifier (e.g., "py", "matlab", "f90")

    Returns:
        Canonical language name or None if not found
    """
    lang_lower = language.lower()

    # Direct match
    if lang_lower in ["python", "octave", "r", "julia", "c", "fortran", "document"]:
        return lang_lower

    # Aliases
    aliases = {
        "py": "python",
        "matlab": "octave",
        "oct": "octave",
        "jl": "julia",
        "cpp": "c",
        "c++": "c",
        "f90": "fortran",
        "f95": "fortran",
        "doc": "document",
    }

    return aliases.get(lang_lower)


# Import runners to trigger registration
from .runners import (
    PythonTester,
    OctaveTester,
    RTester,
    JuliaTester,
    CTester,
    FortranTester,
    DocumentTester,
)

# Re-export base functionality
from .base import BaseTester, TESTERS, register_tester, get_tester

__all__ = [
    "LANGUAGES",
    "list_testers",
    "get_language_name",
    "normalize_language",
    # Base classes
    "BaseTester",
    "TESTERS",
    "register_tester",
    "get_tester",
    # Tester classes
    "PythonTester",
    "OctaveTester",
    "RTester",
    "JuliaTester",
    "CTester",
    "FortranTester",
    "DocumentTester",
]
