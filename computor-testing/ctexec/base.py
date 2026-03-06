"""
Base executor classes for all language testers.

Provides abstract base classes that language-specific executors inherit from,
ensuring consistent interfaces and shared functionality.
"""

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .environment import get_safe_env
from .exceptions import ExecutorError, RuntimeNotFoundError
from .resources import ResourceLimits, make_preexec_fn
from .runtime import check_runtime_installed, get_runtime_info, RuntimeType, get_binary_path


@dataclass
class ExecutorResult:
    """
    Result of code execution.

    Used by all executor types to return execution results
    in a consistent format.
    """

    success: bool
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    return_code: int = 0
    timed_out: bool = False

    # For interpreted languages: extracted variables
    namespace: Dict[str, Any] = field(default_factory=dict)

    # For compiled languages
    compilation_success: bool = True
    compilation_stdout: str = ""
    compilation_stderr: str = ""
    compilation_duration: float = 0.0

    # Error information
    error_message: str = ""
    error_type: str = ""

    def __bool__(self) -> bool:
        """Result is truthy if execution succeeded."""
        return self.success


class BaseExecutor(ABC):
    """
    Abstract base class for all language executors.

    Provides common functionality for environment handling,
    timing, and error management. Language-specific executors
    should inherit from this class and implement the abstract methods.

    Usage:
        # Check if runtime is available
        installed, version = MyExecutor.check_installed()

        # Get path to runtime binary
        path = MyExecutor.get_binary_path()

        # Execute code
        with MyExecutor(working_dir="/path/to/code") as executor:
            result = executor.execute("script.py")
    """

    # Class attributes to be overridden by subclasses
    language: str = ""  # e.g., "python", "r", "julia", "c"
    default_timeout: float = 180.0
    default_compile_timeout: float = 60.0  # For compiled languages

    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
        use_safe_env: bool = True,
        check_runtime: bool = True,
        resource_limits: Optional[ResourceLimits] = None,
    ):
        """
        Initialize the executor.

        Args:
            working_dir: Working directory for execution
            timeout: Timeout in seconds (uses default if None)
            use_safe_env: Use safe environment variables
            check_runtime: Check if runtime is available on init
            resource_limits: Optional resource limits (CPU, memory, etc.)

        Raises:
            RuntimeNotFoundError: If check_runtime=True and runtime not found
        """
        self.working_dir = working_dir or os.getcwd()
        self.timeout = timeout if timeout is not None else self.default_timeout
        self.use_safe_env = use_safe_env
        self.resource_limits = resource_limits

        # Check runtime availability
        if check_runtime and self.language:
            self._verify_runtime()

    @classmethod
    def check_installed(cls, binary: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check if the runtime/compiler for this executor is installed.

        This is a static method that can be called without instantiating
        the executor, useful for pre-flight checks.

        Args:
            binary: Override the default binary name

        Returns:
            Tuple of (is_installed, version_or_error_message)

        Example:
            installed, version = PythonExecutor.check_installed()
            if installed:
                print(f"Python is available: {version}")
        """
        if not cls.language:
            return False, "No language specified for executor"
        return check_runtime_installed(cls.language, binary)

    @classmethod
    def get_binary_path(cls, binary: Optional[str] = None) -> Optional[str]:
        """
        Get the full path to the runtime binary.

        Args:
            binary: Override the default binary name

        Returns:
            Full path to binary or None if not found
        """
        if not cls.language:
            return None
        return get_binary_path(cls.language, binary)

    def _verify_runtime(self) -> None:
        """
        Verify that the required runtime is installed.

        Raises:
            RuntimeNotFoundError: If runtime is not found
        """
        info = get_runtime_info(self.language)
        if info and info.runtime_type == RuntimeType.ANALYZER:
            return  # No external runtime needed

        installed, message = check_runtime_installed(self.language)
        if not installed:
            raise RuntimeNotFoundError(self.language, message)

    def _get_env(self, extra_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get environment variables for execution.

        Args:
            extra_vars: Additional variables to include

        Returns:
            Environment dictionary
        """
        if self.use_safe_env:
            return get_safe_env(self.language, self.working_dir, extra_vars)
        else:
            # Use current environment with blocked vars filtered
            from .environment import filter_env
            env = filter_env(os.environ.copy())
            if extra_vars:
                env.update(extra_vars)
            return env

    def _timed_execution(self, func, *args, **kwargs) -> tuple:
        """
        Execute a function and measure its duration.

        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Tuple of (result, duration_seconds)
        """
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            return result, duration
        except Exception:
            duration = time.perf_counter() - start_time
            raise

    @abstractmethod
    def execute(
        self,
        source_path: str,
        variables_to_extract: Optional[List[str]] = None,
        setup_code: Optional[List[str]] = None,
        teardown_code: Optional[List[str]] = None,
        input_data: Optional[str] = None,
    ) -> ExecutorResult:
        """
        Execute source code and return results.

        This is the main entry point for running code. Subclasses must
        implement this method with language-specific execution logic.

        Args:
            source_path: Path to source file(s)
            variables_to_extract: List of variable names to extract (interpreted)
            setup_code: Code to run before main execution
            teardown_code: Code to run after main execution
            input_data: Data to send to stdin

        Returns:
            ExecutorResult with execution outcome
        """
        pass

    def cleanup(self) -> None:
        """
        Clean up any temporary resources.

        Subclasses should override this to clean up
        temporary files, processes, etc.
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.cleanup()
        return False  # Don't suppress exceptions
