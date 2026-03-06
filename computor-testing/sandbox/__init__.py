"""
Computor Testing Framework - Runner Module

Provides execution backends for running student code.

Supported backends:
- local: Direct subprocess execution (no isolation)
- docker: Full Docker container isolation

Configuration:
    # Via environment variables
    export CT_RUNNER_BACKEND=docker
    export CT_RUNNER_TIMEOUT=30
    export CT_RUNNER_MEMORY_MB=256

    # Via Python API
    from sandbox import configure, run
    configure(backend="docker", timeout=30, memory_mb=256)
    result = run(["python3", "student.py"], cwd="/path/to/submission")
"""

from .executor import (
    SandboxConfig,
    SandboxExecutor,
    ResourceLimits,
    set_resource_limits,
    make_preexec_fn,
    DEFAULT_SAFE_ENV,
    BLOCKED_ENV_VARS,
)

from .security import (
    SafeEnvironment,
    check_dangerous_imports,
    analyze_python_security,
    analyze_c_security,
    analyze_octave_security,
    BLOCKED_PYTHON_MODULES,
    SecurityReport,
    SecurityIssue,
)

from .config import (
    RunnerBackend,
    RunnerSettings,
    get_settings,
    set_settings,
    configure,
    check_backend_available,
    get_available_backends,
    get_best_available_backend,
)

from .backends import (
    Runner,
    LocalRunner,
    DockerRunner,
    get_runner,
)


def run(cmd, stdin=None, cwd=None, env=None, settings=None):
    """
    Run a command with the configured backend.

    This is the main entry point for execution.

    Args:
        cmd: Command and arguments (list)
        stdin: Input to send to stdin
        cwd: Working directory
        env: Additional environment variables
        settings: RunnerSettings (uses global if not provided)

    Returns:
        Dict with stdout, stderr, return_code, timed_out, success

    Example:
        from sandbox import run, configure

        # Configure once
        configure(backend="docker", timeout=30)

        # Run commands
        result = run(["python3", "solution.py"], cwd="./submission")
        print(result['stdout'])
    """
    if settings is None:
        settings = get_settings()

    runner = get_runner(settings)
    return runner.run(cmd, stdin=stdin, cwd=cwd, env=env)


__all__ = [
    # Main API
    "run",
    "configure",

    # Settings
    "RunnerBackend",
    "RunnerSettings",
    "get_settings",
    "set_settings",

    # Backend detection
    "check_backend_available",
    "get_available_backends",
    "get_best_available_backend",

    # Runners
    "Runner",
    "LocalRunner",
    "DockerRunner",
    "get_runner",

    # Legacy executor
    "SandboxConfig",
    "SandboxExecutor",
    "ResourceLimits",
    "set_resource_limits",
    "make_preexec_fn",

    # Environment
    "DEFAULT_SAFE_ENV",
    "BLOCKED_ENV_VARS",
    "SafeEnvironment",

    # Security analysis
    "check_dangerous_imports",
    "analyze_python_security",
    "analyze_c_security",
    "analyze_octave_security",
    "BLOCKED_PYTHON_MODULES",
    "SecurityReport",
    "SecurityIssue",
]
