"""
Language-Specific Test Runners

Each runner is a subclass of BaseTester with language-specific configuration.
"""

from .base import BaseTester, register_tester


@register_tester
class PythonTester(BaseTester):
    """Test runner for Python code."""
    language = "python"


@register_tester
class OctaveTester(BaseTester):
    """Test runner for Octave/MATLAB code."""
    language = "octave"


@register_tester
class RTester(BaseTester):
    """Test runner for R code."""
    language = "r"


@register_tester
class JuliaTester(BaseTester):
    """Test runner for Julia code."""
    language = "julia"


@register_tester
class CTester(BaseTester):
    """Test runner for C/C++ code."""
    language = "c"


@register_tester
class FortranTester(BaseTester):
    """Test runner for Fortran code."""
    language = "fortran"


@register_tester
class DocumentTester(BaseTester):
    """Test runner for document/text analysis."""
    language = "document"


__all__ = [
    "PythonTester",
    "OctaveTester",
    "RTester",
    "JuliaTester",
    "CTester",
    "FortranTester",
    "DocumentTester",
]
