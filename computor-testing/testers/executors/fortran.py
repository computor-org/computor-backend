"""
Fortran code execution module.

This module handles the compilation and execution of Fortran programs,
capturing stdout/stderr and exit codes for testing.

Supports:
- gfortran (GNU Fortran)
- ifort (Intel Fortran)

SECURITY: This module uses safe environment handling to prevent
leaking secrets to compiled programs.
"""

import os
import re
import logging
from typing import Dict, Any, Optional, List, Tuple

from ctexec import CompiledExecutor, ExecutorResult, CompilationResult
from ctexec.exceptions import CompilationError, ExecutionError

logger = logging.getLogger(__name__)

# Fortran specific defaults
FORTRAN_DEFAULTS = {
    "compiler": "gfortran",
    "flags": {
        "f77": ["-Wall", "-std=legacy"],
        "f90": ["-Wall", "-Wextra", "-std=f95", "-fcheck=all"],
        "f95": ["-Wall", "-Wextra", "-std=f95", "-fcheck=all"],
        "f03": ["-Wall", "-Wextra", "-std=f2003", "-fcheck=all"],
        "f08": ["-Wall", "-Wextra", "-std=f2008", "-fcheck=all"],
    },
    "linker": [],
    "timeout": {
        "compile": 60.0,
        "run": 30.0,
    },
    "extensions": {
        "fixed": [".f", ".for", ".ftn", ".F", ".FOR", ".FTN"],
        "free": [".f90", ".f95", ".f03", ".f08", ".f18", ".F90", ".F95", ".F03", ".F08"],
    },
}

# Default compiler settings
DEFAULT_FORTRAN_COMPILER = os.environ.get("FC", FORTRAN_DEFAULTS["compiler"])


class FortranCompilationError(CompilationError):
    """Exception raised when Fortran compilation fails."""
    pass


class FortranExecutionError(ExecutionError):
    """Exception raised when Fortran execution fails."""
    pass


def detect_fortran_standard(source_files: List[str]) -> str:
    """
    Detect the Fortran standard from source files based on extension.

    Args:
        source_files: List of source file paths

    Returns:
        'f77', 'f90', 'f95', 'f03', or 'f08'
    """
    for f in source_files:
        ext = os.path.splitext(f)[1].lower()
        # Fixed format (Fortran 77)
        if ext in ('.f', '.for', '.ftn'):
            return 'f77'
        # Free format (modern Fortran)
        if ext in ('.f90',):
            return 'f90'
        if ext in ('.f95',):
            return 'f95'
        if ext in ('.f03',):
            return 'f03'
        if ext in ('.f08', '.f18'):
            return 'f08'
    return 'f90'  # Default to modern Fortran


class FortranExecutor(CompiledExecutor):
    """
    Executes Fortran code with compilation and stdin/stdout handling.

    This class provides methods to compile and run Fortran programs,
    capturing output for testing purposes.
    """

    language = "fortran"

    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
        compile_timeout: Optional[float] = None,
        check_runtime: bool = True,
    ):
        """
        Initialize the Fortran executor.

        Args:
            working_dir: Directory containing source files
            timeout: Maximum execution time in seconds
            compile_timeout: Maximum compilation time in seconds
            check_runtime: Check if compiler is available
        """
        super().__init__(working_dir, timeout, compile_timeout, check_runtime=check_runtime)
        self._detected_standard = None

    def _get_default_compiler(self) -> str:
        """Get the default compiler command."""
        return DEFAULT_FORTRAN_COMPILER

    def _get_default_flags(self) -> List[str]:
        """Get default compiler flags."""
        flags = ["-Wall", "-Wextra", "-fcheck=all"]

        # Add standard flag based on detected standard
        if self._detected_standard:
            std_map = {
                'f77': 'legacy',
                'f90': 'f95',  # gfortran uses f95 as minimum
                'f95': 'f95',
                'f03': 'f2003',
                'f08': 'f2008',
                'f18': 'f2018',
            }
            std_flag = std_map.get(self._detected_standard, 'f95')
            flags.insert(0, f"-std={std_flag}")

        return flags

    def compile(
        self,
        source_files: List[str],
        compiler: Optional[str] = None,
        flags: Optional[List[str]] = None,
        linker_flags: Optional[List[str]] = None,
        output_name: Optional[str] = None,
    ) -> CompilationResult:
        """
        Compile Fortran source files.

        Overrides parent to add standard auto-detection.

        Args:
            source_files: List of source files (relative to working_dir)
            compiler: Compiler to use (auto-detected if None)
            flags: Compiler flags
            linker_flags: Linker flags
            output_name: Output executable name

        Returns:
            CompilationResult with success status and details
        """
        # Auto-detect Fortran standard from source files
        self._detected_standard = detect_fortran_standard(source_files)

        # Use parent class compile
        return super().compile(
            source_files=source_files,
            compiler=compiler,
            flags=flags,
            linker_flags=linker_flags,
            output_name=output_name,
        )

    def compile_and_run(
        self,
        source_files: List[str],
        args: Optional[List[str]] = None,
        stdin: Optional[str] = None,
        compiler: Optional[str] = None,
        flags: Optional[List[str]] = None,
        linker_flags: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None,
        run_timeout: Optional[float] = None,
    ) -> ExecutorResult:
        """
        Compile and run source files in one operation.

        Args:
            source_files: Source files to compile
            args: Command line arguments
            stdin: Input for the program
            compiler: Compiler to use
            flags: Compiler flags
            linker_flags: Linker flags
            environment: Environment variables (ignored in safe mode)
            run_timeout: Execution timeout

        Returns:
            ExecutorResult with compilation and execution info
        """
        # Auto-detect standard
        self._detected_standard = detect_fortran_standard(source_files)

        # Use parent class method
        return super().compile_and_run(
            source_files=source_files,
            args=args,
            stdin=stdin,
            compiler=compiler,
            flags=flags,
        )


def check_compiler_installed(compiler: str = None) -> Tuple[bool, str]:
    """
    Check if a Fortran compiler is installed.

    Args:
        compiler: Specific compiler to check (default: gfortran)

    Returns:
        Tuple of (is_installed, version_or_error)
    """
    return FortranExecutor.check_installed()


def check_fortran_installed() -> Tuple[bool, str]:
    """
    Check if Fortran compiler (gfortran) is installed.

    Returns:
        Tuple of (is_installed, version_or_error)
    """
    return FortranExecutor.check_installed()


def analyze_source(source_path: str) -> Dict[str, Any]:
    """
    Perform basic static analysis on Fortran source code.

    Args:
        source_path: Path to the source file

    Returns:
        Dictionary with analysis results
    """
    try:
        with open(source_path, 'r') as f:
            content = f.read()
    except Exception as e:
        return {"error": str(e)}

    # Remove comments for analysis (Fortran uses ! for comments in free form)
    lines = content.split('\n')
    content_no_comments = '\n'.join(
        line.split('!')[0] if '!' in line else line
        for line in lines
    )

    analysis = {
        "line_count": len(lines),
        "modules": [],
        "programs": [],
        "subroutines": [],
        "functions": [],
        "uses": [],
        "has_program": False,
        "format": "unknown",
    }

    # Detect format (fixed vs free)
    ext = os.path.splitext(source_path)[1].lower()
    if ext in ('.f', '.for', '.ftn'):
        analysis["format"] = "fixed"
    else:
        analysis["format"] = "free"

    content_lower = content_no_comments.lower()

    # Find program statements
    programs = re.findall(r'\bprogram\s+(\w+)', content_lower)
    analysis["programs"] = programs
    analysis["has_program"] = len(programs) > 0

    # Find modules
    modules = re.findall(r'\bmodule\s+(\w+)', content_lower)
    # Filter out 'module procedure'
    analysis["modules"] = [m for m in modules if m != 'procedure']

    # Find subroutines
    subroutines = re.findall(r'\bsubroutine\s+(\w+)', content_lower)
    analysis["subroutines"] = subroutines

    # Find functions
    functions = re.findall(r'\bfunction\s+(\w+)', content_lower)
    analysis["functions"] = functions

    # Find use statements
    uses = re.findall(r'\buse\s+(\w+)', content_lower)
    analysis["uses"] = list(set(uses))  # Remove duplicates

    # Count keywords
    keywords = {
        'if': len(re.findall(r'\bif\s*\(', content_lower)),
        'do': len(re.findall(r'\bdo\b', content_lower)),
        'while': len(re.findall(r'\bwhile\b', content_lower)),
        'select': len(re.findall(r'\bselect\s+case', content_lower)),
        'allocate': len(re.findall(r'\ballocate\b', content_lower)),
        'deallocate': len(re.findall(r'\bdeallocate\b', content_lower)),
        'call': len(re.findall(r'\bcall\b', content_lower)),
        'return': len(re.findall(r'\breturn\b', content_lower)),
        'read': len(re.findall(r'\bread\b', content_lower)),
        'write': len(re.findall(r'\bwrite\b', content_lower)),
        'print': len(re.findall(r'\bprint\b', content_lower)),
        'open': len(re.findall(r'\bopen\b', content_lower)),
        'close': len(re.findall(r'\bclose\b', content_lower)),
    }
    analysis["keywords"] = {k: v for k, v in keywords.items() if v > 0}

    return analysis
