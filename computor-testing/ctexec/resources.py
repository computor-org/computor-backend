"""
Resource limits for code execution.

Defines resource constraints (CPU, memory, processes, files) that are applied
to every student subprocess. This is the canonical source for resource limit
definitions used by both ctexec executors and the sandbox system.

Every executor gets :func:`default_resource_limits` unless the caller passes
its own, so an untrusted job is never unbounded (#237). The defaults are safe
for numpy/matplotlib workloads and can be tuned per worker through
``COMPUTOR_JOB_*`` environment variables (a value of ``0`` disables that
particular limit):

========================== ======================== =========
variable                   rlimit                   default
========================== ======================== =========
COMPUTOR_JOB_CPU_SECONDS   RLIMIT_CPU (per process) 60
COMPUTOR_JOB_MEMORY_BYTES  RLIMIT_AS                2 GiB
COMPUTOR_JOB_MAX_PROCESSES RLIMIT_NPROC             512
COMPUTOR_JOB_MAX_FILE_SIZE RLIMIT_FSIZE             64 MiB
COMPUTOR_JOB_MAX_OPEN_FILES RLIMIT_NOFILE           256
========================== ======================== =========

RLIMIT_CORE is always 0. Note that the kernel counts RLIMIT_NPROC per real
UID (threads included), not per job: it caps the number of tasks the worker
UID may own when a job forks, so it bounds a fork bomb but must stay well above
the worker's own thread count. Container-level ``pids_limit`` is the hard cap.
"""

import logging
import os
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MIB = 1024 * 1024
GIB = 1024 * MIB

# (env var, default) for each tunable limit.
_ENV_DEFAULTS = {
    "cpu_seconds": ("COMPUTOR_JOB_CPU_SECONDS", 60),
    "memory_bytes": ("COMPUTOR_JOB_MEMORY_BYTES", 2 * GIB),
    "max_processes": ("COMPUTOR_JOB_MAX_PROCESSES", 512),
    "max_file_size_bytes": ("COMPUTOR_JOB_MAX_FILE_SIZE", 64 * MIB),
    "max_files": ("COMPUTOR_JOB_MAX_OPEN_FILES", 256),
}


@dataclass
class ResourceLimits:
    """Resource limits for code execution. ``0`` means "do not limit"."""

    # Time limits
    timeout: float = 30.0
    cpu_seconds: int = 60

    # Memory limit (bytes, address space)
    memory_bytes: int = 2 * GIB

    # Process limits
    max_processes: int = 512
    max_files: int = 256
    max_file_size_bytes: int = 64 * MIB

    # Network
    network_enabled: bool = False


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("Ignoring non-integer %s=%r, using %s", name, raw, default)
        return default
    return max(0, value)


def default_resource_limits() -> ResourceLimits:
    """The per-job limits every executor applies unless told otherwise."""
    return ResourceLimits(
        **{field: _env_int(var, default)
           for field, (var, default) in _ENV_DEFAULTS.items()}
    )


def _clamp_setrlimit(resource_mod, which: int, value: int) -> None:
    """Lower soft and hard limit to ``value``, never above the current hard.

    An unprivileged process cannot raise its hard limit, so asking for more
    than the inherited hard limit would fail; keep the stricter one instead.
    """
    _soft, hard = resource_mod.getrlimit(which)
    if hard != resource_mod.RLIM_INFINITY:
        value = min(value, hard)
    resource_mod.setrlimit(which, (value, value))


def set_resource_limits(limits: ResourceLimits) -> None:
    """
    Set resource limits for the current process.

    This should be called in a subprocess before exec (via preexec_fn).
    Only works on Unix-like systems. Limits of 0 are left untouched.
    """
    if sys.platform == 'win32':
        logger.warning("Resource limits not supported on Windows")
        return

    import resource

    pairs = (
        (resource.RLIMIT_CPU, limits.cpu_seconds),
        (resource.RLIMIT_AS, limits.memory_bytes),
        (resource.RLIMIT_FSIZE, limits.max_file_size_bytes),
        (resource.RLIMIT_NPROC, limits.max_processes),
        (resource.RLIMIT_NOFILE, limits.max_files),
    )
    for which, value in pairs:
        if value and value > 0:
            _clamp_setrlimit(resource, which, int(value))
    # Never write core dumps of student processes.
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def make_preexec_fn(limits: ResourceLimits):
    """
    Create a preexec_fn that applies resource limits.

    Returns None on Windows where resource limits aren't supported.
    """
    if sys.platform == 'win32':
        return None

    def _apply_limits():
        set_resource_limits(limits)

    return _apply_limits
