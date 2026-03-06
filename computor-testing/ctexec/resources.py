"""
Resource limits for code execution.

Defines resource constraints (CPU, memory, processes, files) that can be
applied to subprocess execution. This is the canonical source for resource
limit definitions used by both ctexec executors and the sandbox system.
"""

import sys
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits for code execution."""

    # Time limits
    timeout: float = 30.0
    cpu_seconds: int = 30

    # Memory limits (bytes)
    memory_bytes: int = 256 * 1024 * 1024  # 256 MB

    # Process limits
    max_processes: int = 10
    max_files: int = 50
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10 MB

    # Network
    network_enabled: bool = False


def set_resource_limits(limits: ResourceLimits) -> None:
    """
    Set resource limits for the current process.

    This should be called in a subprocess before exec (via preexec_fn).
    Only works on Unix-like systems.

    Args:
        limits: ResourceLimits configuration
    """
    if sys.platform == 'win32':
        logger.warning("Resource limits not supported on Windows")
        return

    import resource

    # CPU time limit
    resource.setrlimit(
        resource.RLIMIT_CPU,
        (limits.cpu_seconds, limits.cpu_seconds)
    )

    # Memory limit (address space)
    resource.setrlimit(
        resource.RLIMIT_AS,
        (limits.memory_bytes, limits.memory_bytes)
    )

    # File size limit
    resource.setrlimit(
        resource.RLIMIT_FSIZE,
        (limits.max_file_size_bytes, limits.max_file_size_bytes)
    )

    # Number of processes
    resource.setrlimit(
        resource.RLIMIT_NPROC,
        (limits.max_processes, limits.max_processes)
    )

    # Number of open files
    resource.setrlimit(
        resource.RLIMIT_NOFILE,
        (limits.max_files, limits.max_files)
    )

    logger.debug(
        f"Resource limits set: CPU={limits.cpu_seconds}s, "
        f"MEM={limits.memory_bytes // (1024*1024)}MB, "
        f"PROCS={limits.max_processes}"
    )


def make_preexec_fn(limits: ResourceLimits):
    """
    Create a preexec_fn that applies resource limits.

    Returns None on Windows where resource limits aren't supported.

    Args:
        limits: ResourceLimits to apply

    Returns:
        Callable for subprocess preexec_fn, or None on Windows
    """
    if sys.platform == 'win32':
        return None

    def _apply_limits():
        set_resource_limits(limits)

    return _apply_limits
