"""
Unified runtime/compiler detection for all languages.

Provides a single interface to check if language runtimes
and compilers are installed and get their version information.
"""

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class RuntimeType(Enum):
    """Type of language runtime."""

    INTERPRETER = "interpreter"  # Python, R, Julia, Octave
    COMPILER = "compiler"  # gcc, gfortran
    ANALYZER = "analyzer"  # Document analysis (no external runtime)


@dataclass
class RuntimeInfo:
    """Information about a language runtime."""

    name: str  # Human-readable name
    language: str  # Language key
    binary: str  # Default binary name
    version_flag: str = "--version"  # Flag to get version
    runtime_type: RuntimeType = RuntimeType.INTERPRETER
    version_output: str = "stdout"  # Where version info appears: "stdout", "stderr", "first_line"
    alt_binaries: List[str] = None  # Alternative binary names to try

    def __post_init__(self):
        if self.alt_binaries is None:
            self.alt_binaries = []


# Registry of all supported runtimes
RUNTIMES: Dict[str, RuntimeInfo] = {
    "python": RuntimeInfo(
        name="Python",
        language="python",
        binary="python3",
        runtime_type=RuntimeType.INTERPRETER,
        alt_binaries=["python"],
    ),
    "octave": RuntimeInfo(
        name="GNU Octave",
        language="octave",
        binary="octave-cli",
        version_output="first_line",
        alt_binaries=["octave"],
    ),
    "r": RuntimeInfo(
        name="R",
        language="r",
        binary="Rscript",
        version_output="stderr",  # R outputs version to stderr
        alt_binaries=["R"],
    ),
    "julia": RuntimeInfo(
        name="Julia",
        language="julia",
        binary="julia",
        version_output="stdout",
    ),
    "c": RuntimeInfo(
        name="GCC (C)",
        language="c",
        binary="gcc",
        runtime_type=RuntimeType.COMPILER,
        version_output="first_line",
        alt_binaries=["clang", "cc"],
    ),
    "cpp": RuntimeInfo(
        name="G++ (C++)",
        language="cpp",
        binary="g++",
        runtime_type=RuntimeType.COMPILER,
        version_output="first_line",
        alt_binaries=["clang++", "c++"],
    ),
    "fortran": RuntimeInfo(
        name="GFortran",
        language="fortran",
        binary="gfortran",
        runtime_type=RuntimeType.COMPILER,
        version_output="first_line",
        alt_binaries=["ifort", "flang"],
    ),
    "document": RuntimeInfo(
        name="Document Analyzer",
        language="document",
        binary="",
        runtime_type=RuntimeType.ANALYZER,
    ),
}


def check_runtime_installed(
    language: str,
    binary: Optional[str] = None,
    timeout: float = 10.0,
) -> Tuple[bool, str]:
    """
    Check if a runtime/compiler is installed.

    Args:
        language: Language key (python, octave, r, julia, c, cpp, fortran, document)
        binary: Override the default binary name
        timeout: Timeout for version check in seconds

    Returns:
        Tuple of (is_installed, version_or_error_message)
    """
    lang_lower = language.lower()

    if lang_lower not in RUNTIMES:
        return False, f"Unknown language: {language}"

    info = RUNTIMES[lang_lower]

    # Document analyzer doesn't need external runtime
    if info.runtime_type == RuntimeType.ANALYZER:
        return True, "Built-in text analyzer"

    # Determine which binary to check
    binary = binary or info.binary

    # Try the specified binary
    result = _check_binary(binary, info.version_flag, info.version_output, timeout)
    if result[0]:
        return result

    # Try alternative binaries if main one fails
    if not binary or binary == info.binary:
        for alt in info.alt_binaries:
            result = _check_binary(alt, info.version_flag, info.version_output, timeout)
            if result[0]:
                return result

    return False, f"{info.name} not found (tried: {binary})"


def _check_binary(
    binary: str,
    version_flag: str,
    version_output: str,
    timeout: float,
) -> Tuple[bool, str]:
    """
    Check if a specific binary is available.

    Args:
        binary: Binary name to check
        version_flag: Flag to pass for version info
        version_output: Where to find version ("stdout", "stderr", "first_line")
        timeout: Timeout in seconds

    Returns:
        Tuple of (is_installed, version_or_error)
    """
    try:
        result = subprocess.run(
            [binary, version_flag],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode == 0:
            # Parse version based on output location
            if version_output == "stderr":
                output = result.stderr.strip()
            elif version_output == "first_line":
                output = (result.stdout or result.stderr).split("\n")[0].strip()
            else:
                output = result.stdout.strip()

            return True, f"{output} ({binary})"

        return False, f"{binary} returned exit code {result.returncode}"

    except FileNotFoundError:
        return False, f"Binary not found: {binary}"
    except subprocess.TimeoutExpired:
        return False, f"{binary} version check timed out"
    except PermissionError:
        return False, f"Permission denied: {binary}"
    except Exception as e:
        return False, f"Error checking {binary}: {str(e)}"


def get_runtime_info(language: str) -> Optional[RuntimeInfo]:
    """
    Get runtime information for a language.

    Args:
        language: Language key

    Returns:
        RuntimeInfo or None if language not found
    """
    return RUNTIMES.get(language.lower())


def list_available_runtimes() -> Dict[str, Tuple[bool, str]]:
    """
    Check all supported runtimes and return their status.

    Returns:
        Dictionary mapping language -> (is_installed, version_or_error)
    """
    return {lang: check_runtime_installed(lang) for lang in RUNTIMES}


def get_binary_path(language: str, binary: Optional[str] = None) -> Optional[str]:
    """
    Get the full path to a runtime binary.

    Args:
        language: Language key
        binary: Override the default binary name

    Returns:
        Full path to binary or None if not found
    """
    import shutil

    lang_lower = language.lower()
    if lang_lower not in RUNTIMES:
        return None

    info = RUNTIMES[lang_lower]

    # Document analyzer has no binary
    if info.runtime_type == RuntimeType.ANALYZER:
        return None

    # Check specified binary or default
    binary = binary or info.binary
    path = shutil.which(binary)
    if path:
        return path

    # Try alternatives
    for alt in info.alt_binaries:
        path = shutil.which(alt)
        if path:
            return path

    return None
