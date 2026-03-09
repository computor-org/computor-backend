"""
C/C++ code execution module.

This module handles the compilation and execution of C/C++ programs,
capturing stdout/stderr and exit codes for testing.

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

# Default compiler settings
DEFAULT_C_COMPILER = os.environ.get("CC", "gcc")
DEFAULT_CXX_COMPILER = os.environ.get("CXX", "g++")


class CCompilationError(CompilationError):
    """Exception raised when C/C++ compilation fails."""
    pass


class CExecutionError(ExecutionError):
    """Exception raised when C/C++ execution fails."""
    pass


def detect_language(source_files: List[str]) -> str:
    """
    Detect the programming language from source files.

    Args:
        source_files: List of source file paths

    Returns:
        'c' or 'cpp'
    """
    for f in source_files:
        ext = os.path.splitext(f)[1].lower()
        if ext in ('.cpp', '.cxx', '.cc', '.C', '.hpp', '.hxx'):
            return 'cpp'
    return 'c'


def detect_compiler(language: str, preferred: Optional[str] = None) -> str:
    """
    Detect the appropriate compiler.

    Args:
        language: 'c' or 'cpp'
        preferred: Preferred compiler (if specified)

    Returns:
        Compiler command
    """
    if preferred:
        return preferred

    if language == 'cpp':
        return DEFAULT_CXX_COMPILER
    return DEFAULT_C_COMPILER


class CExecutor(CompiledExecutor):
    """
    Executes C/C++ code with compilation and stdin/stdout handling.

    This class provides methods to compile and run C/C++ programs,
    capturing output for testing purposes.
    """

    language = "c"  # Default to C, will auto-detect cpp if needed

    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
        compile_timeout: Optional[float] = None,
        check_runtime: bool = True,
    ):
        """
        Initialize the C/C++ executor.

        Args:
            working_dir: Directory containing source files
            timeout: Maximum execution time in seconds
            compile_timeout: Maximum compilation time in seconds
            check_runtime: Check if compiler is available
        """
        super().__init__(working_dir, timeout, compile_timeout, check_runtime=check_runtime)
        self._detected_language = None

    def _get_default_compiler(self) -> str:
        """Get the default compiler command."""
        if self._detected_language == 'cpp':
            return DEFAULT_CXX_COMPILER
        return DEFAULT_C_COMPILER

    def _get_default_flags(self) -> List[str]:
        """Get default compiler flags."""
        return ["-Wall", "-Wextra"]

    def compile(
        self,
        source_files: List[str],
        compiler: Optional[str] = None,
        flags: Optional[List[str]] = None,
        linker_flags: Optional[List[str]] = None,
        output_name: Optional[str] = None,
    ) -> CompilationResult:
        """
        Compile C/C++ source files.

        Overrides parent to add language auto-detection.

        Args:
            source_files: List of source files (relative to working_dir)
            compiler: Compiler to use (auto-detected if None)
            flags: Compiler flags
            linker_flags: Linker flags
            output_name: Output executable name

        Returns:
            CompilationResult with success status and details
        """
        # Auto-detect language from source files
        self._detected_language = detect_language(source_files)

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

        This is the legacy interface that returns ExecutorResult directly.

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
        # Auto-detect language
        self._detected_language = detect_language(source_files)

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
    Check if a C/C++ compiler is installed.

    Args:
        compiler: Specific compiler to check (default: gcc)

    Returns:
        Tuple of (is_installed, version_or_error)
    """
    return CExecutor.check_installed()


def check_c_installed() -> Tuple[bool, str]:
    """
    Check if C compiler (gcc) is installed.

    Returns:
        Tuple of (is_installed, version_or_error)
    """
    return CExecutor.check_installed()


def analyze_source(source_path: str) -> Dict[str, Any]:
    """
    Perform basic static analysis on C/C++ source code.

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

    # Remove comments for analysis
    # Remove single-line comments
    content_no_comments = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    # Remove multi-line comments
    content_no_comments = re.sub(r'/\*.*?\*/', '', content_no_comments, flags=re.DOTALL)

    analysis = {
        "line_count": len(content.split('\n')),
        "includes": [],
        "functions": [],
        "main_function": False,
        "keywords": {},
    }

    # Find includes
    analysis["includes"] = re.findall(r'#include\s*[<"]([^>"]+)[>"]', content)

    # Check for main function
    analysis["main_function"] = bool(re.search(
        r'\b(int|void)\s+main\s*\(', content_no_comments
    ))

    # Find function definitions (simplified)
    func_pattern = r'\b(\w+)\s+(\w+)\s*\([^)]*\)\s*\{'
    for match in re.finditer(func_pattern, content_no_comments):
        func_name = match.group(2)
        if func_name not in ('if', 'while', 'for', 'switch'):
            analysis["functions"].append(func_name)

    # Count keywords
    keywords = ['if', 'else', 'for', 'while', 'do', 'switch', 'case',
                'return', 'break', 'continue', 'goto', 'struct', 'class',
                'typedef', 'enum', 'union', 'malloc', 'free', 'new', 'delete']

    for kw in keywords:
        count = len(re.findall(rf'\b{kw}\b', content_no_comments))
        if count > 0:
            analysis["keywords"][kw] = count

    return analysis
