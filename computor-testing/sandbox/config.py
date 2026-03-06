"""
Runner Configuration

Allows users to configure which execution backend to use.
"""

import os
import shutil
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


class RunnerBackend(Enum):
    """Available execution backends."""

    # Local execution - direct subprocess, no isolation
    LOCAL = "local"

    # Docker - full container isolation
    DOCKER = "docker"


@dataclass
class RunnerSettings:
    """
    Global runner settings.

    Can be configured via:
    - Environment variables (CT_RUNNER_BACKEND, etc.)
    - Configuration file
    - Programmatic API
    """

    # Which backend to use
    backend: RunnerBackend = RunnerBackend.LOCAL

    # Resource limits (used by Docker)
    timeout: float = 30.0
    memory_mb: int = 256
    cpu_seconds: int = 30
    max_processes: int = 10
    max_files: int = 50
    max_file_size_mb: int = 10

    # Network
    network_enabled: bool = False

    # Environment
    clean_environment: bool = True
    env_whitelist: list = field(default_factory=list)

    # Docker-specific options
    docker_image: str = "ct-sandbox:latest"

    @classmethod
    def from_environment(cls) -> "RunnerSettings":
        """Load settings from environment variables."""
        settings = cls()

        # Backend selection (support both CT_RUNNER_BACKEND and CT_SANDBOX_BACKEND for backwards compat)
        backend_str = os.environ.get(
            "CT_RUNNER_BACKEND",
            os.environ.get("CT_SANDBOX_BACKEND", "local")
        ).lower()

        # Map old values to new
        if backend_str in ("none", "rlimit", "firejail", "bubblewrap", "nsjail"):
            backend_str = "local"

        try:
            settings.backend = RunnerBackend(backend_str)
        except ValueError:
            pass  # Keep default

        # Resource limits (support both CT_RUNNER_* and CT_SANDBOX_* for backwards compat)
        if "CT_RUNNER_TIMEOUT" in os.environ:
            settings.timeout = float(os.environ["CT_RUNNER_TIMEOUT"])
        elif "CT_SANDBOX_TIMEOUT" in os.environ:
            settings.timeout = float(os.environ["CT_SANDBOX_TIMEOUT"])

        if "CT_RUNNER_MEMORY_MB" in os.environ:
            settings.memory_mb = int(os.environ["CT_RUNNER_MEMORY_MB"])
        elif "CT_SANDBOX_MEMORY_MB" in os.environ:
            settings.memory_mb = int(os.environ["CT_SANDBOX_MEMORY_MB"])

        if "CT_RUNNER_CPU_SECONDS" in os.environ:
            settings.cpu_seconds = int(os.environ["CT_RUNNER_CPU_SECONDS"])
        elif "CT_SANDBOX_CPU_SECONDS" in os.environ:
            settings.cpu_seconds = int(os.environ["CT_SANDBOX_CPU_SECONDS"])

        if "CT_RUNNER_MAX_PROCESSES" in os.environ:
            settings.max_processes = int(os.environ["CT_RUNNER_MAX_PROCESSES"])
        elif "CT_SANDBOX_MAX_PROCESSES" in os.environ:
            settings.max_processes = int(os.environ["CT_SANDBOX_MAX_PROCESSES"])

        # Network
        if "CT_RUNNER_NETWORK" in os.environ:
            settings.network_enabled = os.environ["CT_RUNNER_NETWORK"].lower() in ("1", "true", "yes")
        elif "CT_SANDBOX_NETWORK" in os.environ:
            settings.network_enabled = os.environ["CT_SANDBOX_NETWORK"].lower() in ("1", "true", "yes")

        # Environment
        if "CT_RUNNER_CLEAN_ENV" in os.environ:
            settings.clean_environment = os.environ["CT_RUNNER_CLEAN_ENV"].lower() in ("1", "true", "yes")
        elif "CT_SANDBOX_CLEAN_ENV" in os.environ:
            settings.clean_environment = os.environ["CT_SANDBOX_CLEAN_ENV"].lower() in ("1", "true", "yes")

        # Docker
        if "CT_RUNNER_DOCKER_IMAGE" in os.environ:
            settings.docker_image = os.environ["CT_RUNNER_DOCKER_IMAGE"]
        elif "CT_SANDBOX_DOCKER_IMAGE" in os.environ:
            settings.docker_image = os.environ["CT_SANDBOX_DOCKER_IMAGE"]

        return settings

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunnerSettings":
        """Load settings from a dictionary (e.g., from YAML config)."""
        settings = cls()

        if "backend" in data:
            backend_str = data["backend"].lower()
            # Map old values to new
            if backend_str in ("none", "rlimit", "firejail", "bubblewrap", "nsjail"):
                backend_str = "local"
            try:
                settings.backend = RunnerBackend(backend_str)
            except ValueError:
                pass

        # Simple fields
        for field_name in ["timeout", "memory_mb", "cpu_seconds", "max_processes",
                          "max_files", "max_file_size_mb", "network_enabled",
                          "clean_environment", "docker_image"]:
            if field_name in data:
                setattr(settings, field_name, data[field_name])

        if "env_whitelist" in data:
            settings.env_whitelist = list(data["env_whitelist"])

        return settings

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "backend": self.backend.value,
            "timeout": self.timeout,
            "memory_mb": self.memory_mb,
            "cpu_seconds": self.cpu_seconds,
            "max_processes": self.max_processes,
            "max_files": self.max_files,
            "max_file_size_mb": self.max_file_size_mb,
            "network_enabled": self.network_enabled,
            "clean_environment": self.clean_environment,
            "env_whitelist": self.env_whitelist,
            "docker_image": self.docker_image,
        }


def check_backend_available(backend: RunnerBackend) -> tuple[bool, str]:
    """
    Check if a backend is available on the system.

    Returns:
        Tuple of (available, message)
    """
    if backend == RunnerBackend.LOCAL:
        return True, "Local execution (always available)"

    if backend == RunnerBackend.DOCKER:
        path = shutil.which("docker")
        if path:
            # Check if docker daemon is running
            import subprocess
            try:
                result = subprocess.run(
                    ["docker", "info"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return True, "Docker available and running"
                return False, "Docker installed but daemon not running"
            except Exception as e:
                return False, f"Docker check failed: {e}"
        return False, "docker not found in PATH"

    return False, f"Unknown backend: {backend}"


def get_available_backends() -> Dict[RunnerBackend, str]:
    """Get all available backends on this system."""
    available = {}
    for backend in RunnerBackend:
        is_available, message = check_backend_available(backend)
        if is_available:
            available[backend] = message
    return available


def get_best_available_backend() -> RunnerBackend:
    """
    Get the most secure available backend.

    Priority: docker > local
    """
    if check_backend_available(RunnerBackend.DOCKER)[0]:
        return RunnerBackend.DOCKER
    return RunnerBackend.LOCAL


# Global settings instance - can be modified at runtime
_global_settings: Optional[RunnerSettings] = None


def get_settings() -> RunnerSettings:
    """Get the global runner settings."""
    global _global_settings
    if _global_settings is None:
        _global_settings = RunnerSettings.from_environment()
    return _global_settings


def set_settings(settings: RunnerSettings) -> None:
    """Set the global runner settings."""
    global _global_settings
    _global_settings = settings


def configure(
    backend: Optional[str] = None,
    timeout: Optional[float] = None,
    memory_mb: Optional[int] = None,
    network: Optional[bool] = None,
    **kwargs
) -> RunnerSettings:
    """
    Configure runner settings.

    Args:
        backend: Backend name ("local", "docker")
        timeout: Execution timeout in seconds
        memory_mb: Memory limit in MB
        network: Enable network access
        **kwargs: Additional settings

    Returns:
        Updated RunnerSettings
    """
    settings = get_settings()

    if backend is not None:
        backend_lower = backend.lower()
        # Map old values to new
        if backend_lower in ("none", "rlimit", "firejail", "bubblewrap", "nsjail"):
            backend_lower = "local"
        try:
            settings.backend = RunnerBackend(backend_lower)
        except ValueError:
            raise ValueError(f"Unknown backend: {backend}. "
                           f"Available: {[b.value for b in RunnerBackend]}")

    if timeout is not None:
        settings.timeout = timeout
        settings.cpu_seconds = int(timeout)

    if memory_mb is not None:
        settings.memory_mb = memory_mb

    if network is not None:
        settings.network_enabled = network

    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)

    set_settings(settings)
    return settings
