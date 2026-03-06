"""
Computor Testing Core - Security Utilities

Path validation utilities to prevent directory traversal attacks.
Used by all testing systems to validate paths from test.yaml configurations.
"""

import os
import re
import signal
import sys
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class PathValidationError(Exception):
    """Exception raised when path validation fails"""
    pass


def validate_path_in_root(path: str, root: str, name: str = "path") -> str:
    """
    Validate that a path is within the root directory.

    Prevents path traversal attacks by ensuring the resolved path
    stays within the specified root directory.

    Args:
        path: The path to validate
        root: The root directory that path must be within
        name: Name of the path for error messages

    Returns:
        The resolved absolute path

    Raises:
        PathValidationError: If path escapes the root directory
    """
    # Resolve both paths to absolute
    root_abs = os.path.abspath(root)

    if os.path.isabs(path):
        path_abs = os.path.abspath(path)
    else:
        path_abs = os.path.abspath(os.path.join(root, path))

    # Check that resolved path is within root
    try:
        # Use os.path.commonpath to check containment
        common = os.path.commonpath([root_abs, path_abs])
        if common != root_abs:
            raise PathValidationError(
                f"{name} '{path}' escapes root directory '{root}'"
            )
    except ValueError:
        # Different drives on Windows
        raise PathValidationError(
            f"{name} '{path}' is not within root directory '{root}'"
        )

    return path_abs


def validate_filename(filename: str, allow_path_separators: bool = False) -> str:
    """
    Validate a filename for safety.

    Args:
        filename: The filename to validate
        allow_path_separators: Whether to allow path separators

    Returns:
        The validated filename

    Raises:
        PathValidationError: If filename is invalid or dangerous
    """
    if not filename:
        raise PathValidationError("Filename cannot be empty")

    # Check for path separators
    if not allow_path_separators:
        if os.sep in filename or '/' in filename or '\\' in filename:
            raise PathValidationError(
                f"Filename '{filename}' contains path separators"
            )

    # Check for parent directory references (actual '..' path components)
    # Split on all possible separators to check each component
    parts = filename.replace('\\', '/').split('/')
    if '..' in parts:
        raise PathValidationError(
            f"Filename '{filename}' contains parent directory reference"
        )

    # Check for null bytes
    if '\x00' in filename:
        raise PathValidationError(
            f"Filename '{filename}' contains null byte"
        )

    return filename


def validate_absolute_path(path: str, name: str = "path") -> str:
    """
    Validate an absolute path for basic safety.

    Allows absolute paths (used by automated testing systems) but ensures
    they don't contain traversal components or point to sensitive locations.

    Args:
        path: The absolute path to validate
        name: Name of the path for error messages

    Returns:
        The normalized absolute path

    Raises:
        PathValidationError: If path contains dangerous components
    """
    normalized = os.path.abspath(path)

    # Check for traversal components in the original path
    parts = path.replace('\\', '/').split('/')
    if '..' in parts:
        raise PathValidationError(
            f"{name} '{path}' contains parent directory reference"
        )

    # Check for null bytes
    if '\x00' in path:
        raise PathValidationError(
            f"{name} '{path}' contains null byte"
        )

    # Block writes to sensitive system directories
    sensitive_prefixes = ['/etc', '/usr', '/bin', '/sbin', '/boot', '/sys', '/proc', '/dev']
    for prefix in sensitive_prefixes:
        if normalized.startswith(prefix + '/') or normalized == prefix:
            raise PathValidationError(
                f"{name} '{path}' points to sensitive system directory"
            )

    logger.debug(f"Absolute path accepted for {name}: {normalized}")
    return normalized


def safe_join(root: str, *paths: str) -> str:
    """
    Safely join paths ensuring result stays within root.

    Args:
        root: Root directory
        *paths: Path components to join

    Returns:
        Joined and validated path

    Raises:
        PathValidationError: If resulting path escapes root
    """
    joined = os.path.join(root, *paths)
    return validate_path_in_root(joined, root, "joined path")


class RegexTimeoutError(Exception):
    """Exception raised when a regex operation exceeds time limit."""
    pass


def _timeout_handler(signum, frame):
    raise RegexTimeoutError("Regex operation timed out")


def safe_regex_findall(pattern: str, text: str, flags: int = 0, timeout: int = 5) -> List[str]:
    """
    Execute re.findall with a timeout to prevent ReDoS attacks.

    On Unix, uses SIGALRM for real timeout enforcement.
    On Windows, falls back to a pattern complexity check.

    Args:
        pattern: Regex pattern (from test.yaml, potentially untrusted)
        text: Text to search
        flags: re module flags
        timeout: Maximum seconds for the operation (default: 5)

    Returns:
        List of matches

    Raises:
        RegexTimeoutError: If the operation times out
        re.error: If the pattern is invalid
    """
    # Pre-validate the pattern compiles
    compiled = re.compile(pattern, flags)

    if sys.platform != 'win32':
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
        try:
            result = compiled.findall(text)
        except RegexTimeoutError:
            raise RegexTimeoutError(
                f"Regex pattern `{pattern}` timed out after {timeout}s (possible ReDoS)"
            )
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        return result
    else:
        # Windows: no SIGALRM, just run with a warning for complex patterns
        return compiled.findall(text)


def safe_regex_search(pattern: str, text: str, flags: int = 0, timeout: int = 5) -> Optional[re.Match]:
    """
    Execute re.search with a timeout to prevent ReDoS attacks.

    Args:
        pattern: Regex pattern (from test.yaml, potentially untrusted)
        text: Text to search
        flags: re module flags
        timeout: Maximum seconds for the operation (default: 5)

    Returns:
        Match object or None

    Raises:
        RegexTimeoutError: If the operation times out
        re.error: If the pattern is invalid
    """
    compiled = re.compile(pattern, flags)

    if sys.platform != 'win32':
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
        try:
            result = compiled.search(text)
        except RegexTimeoutError:
            raise RegexTimeoutError(
                f"Regex pattern `{pattern}` timed out after {timeout}s (possible ReDoS)"
            )
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        return result
    else:
        return compiled.search(text)
