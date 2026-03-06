"""
Computor Executor Core (catexec)

Unified execution infrastructure for all language testers.
Provides base classes, environment handling, and runtime detection.

Architecture:
    BaseExecutor (abstract)
    ├── InterpretedExecutor (Python, R, Julia, Octave)
    │   └── Runs scripts in subprocess, extracts variables via JSON
    └── CompiledExecutor (C, C++, Fortran)
        └── Compiles to executable, captures stdout/stderr
"""

from .exceptions import (
    ExecutorError,
    ExecutionError,
    CompilationError,
    RuntimeNotFoundError,
    ExecutionTimeoutError,
    TimeoutError,  # backward-compatible alias for ExecutionTimeoutError
)

from .environment import (
    BLOCKED_ENV_VARS,
    DEFAULT_SAFE_ENV,
    get_safe_env,
    filter_env,
)

from .runtime import (
    RuntimeType,
    RuntimeInfo,
    RUNTIMES,
    check_runtime_installed,
    get_runtime_info,
    list_available_runtimes,
    get_binary_path,
)

from .base import (
    ExecutorResult,
    BaseExecutor,
)

from .interpreted import (
    InterpretedExecutor,
)

from .compiled import (
    CompilationResult,
    CompiledExecutor,
)

from .resources import (
    ResourceLimits,
    set_resource_limits,
    make_preexec_fn,
)

__version__ = "0.1.0"
__all__ = [
    # Exceptions
    "ExecutorError",
    "ExecutionError",
    "CompilationError",
    "RuntimeNotFoundError",
    "ExecutionTimeoutError",
    "TimeoutError",  # backward-compatible alias
    # Environment
    "BLOCKED_ENV_VARS",
    "DEFAULT_SAFE_ENV",
    "get_safe_env",
    "filter_env",
    # Runtime
    "RuntimeType",
    "RuntimeInfo",
    "RUNTIMES",
    "check_runtime_installed",
    "get_runtime_info",
    "list_available_runtimes",
    "get_binary_path",
    # Base
    "ExecutorResult",
    "BaseExecutor",
    # Interpreted
    "InterpretedExecutor",
    # Compiled
    "CompilationResult",
    "CompiledExecutor",
    # Resources
    "ResourceLimits",
    "set_resource_limits",
    "make_preexec_fn",
]
