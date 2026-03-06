"""
Runner Backend Implementations

Provides local and Docker execution backends.
"""

import os
import subprocess
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from .config import RunnerSettings, RunnerBackend
from .executor import DEFAULT_SAFE_ENV, BLOCKED_ENV_VARS


class Runner(ABC):
    """Abstract base class for runners."""

    def __init__(self, settings: RunnerSettings):
        self.settings = settings

    @abstractmethod
    def run(self, cmd: List[str],
            stdin: Optional[str] = None,
            cwd: Optional[str] = None,
            env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Run a command.

        Returns:
            Dict with stdout, stderr, return_code, timed_out, success
        """
        pass

    def _get_safe_env(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build safe environment."""
        if not self.settings.clean_environment:
            env = {k: v for k, v in os.environ.items()
                   if k.upper() not in BLOCKED_ENV_VARS}
        else:
            env = DEFAULT_SAFE_ENV.copy()

        # Add whitelisted vars
        for key in self.settings.env_whitelist:
            if key in os.environ:
                env[key] = os.environ[key]

        # Add extra vars
        if extra:
            for key, value in extra.items():
                if key.upper() not in BLOCKED_ENV_VARS:
                    env[key] = value

        return env


class LocalRunner(Runner):
    """Local execution - direct subprocess."""

    def run(self, cmd: List[str],
            stdin: Optional[str] = None,
            cwd: Optional[str] = None,
            env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:

        actual_env = self._get_safe_env(env) if self.settings.clean_environment else None

        try:
            result = subprocess.run(
                cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=self.settings.timeout,
                cwd=cwd,
                env=actual_env,
            )
            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'timed_out': False,
                'success': True,
            }
        except subprocess.TimeoutExpired as e:
            return {
                'stdout': e.stdout.decode() if e.stdout else '',
                'stderr': e.stderr.decode() if e.stderr else '',
                'return_code': -1,
                'timed_out': True,
                'success': False,
            }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'return_code': -1,
                'timed_out': False,
                'success': False,
            }


class DockerRunner(Runner):
    """Docker container execution."""

    def run(self, cmd: List[str],
            stdin: Optional[str] = None,
            cwd: Optional[str] = None,
            env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:

        actual_env = self._get_safe_env(env)

        # Build docker command
        docker_cmd = [
            "docker", "run",
            "--rm",
            "--user", "1000:1000",
            "--read-only",
            "--tmpfs", "/tmp:size=100M,mode=1777",
            f"--memory={self.settings.memory_mb}m",
            f"--memory-swap={self.settings.memory_mb}m",
            "--cpus=1",
            f"--pids-limit={self.settings.max_processes}",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
        ]

        # Network
        if not self.settings.network_enabled:
            docker_cmd.append("--network=none")

        # Environment variables
        for key, value in actual_env.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        # Working directory mount
        if cwd:
            docker_cmd.extend(["-v", f"{cwd}:/sandbox:rw"])
            docker_cmd.extend(["-w", "/sandbox"])

        # Image
        docker_cmd.append(self.settings.docker_image)

        # Command
        docker_cmd.extend(cmd)

        try:
            result = subprocess.run(
                docker_cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=self.settings.timeout + 5,  # Extra time for container startup
            )
            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'timed_out': False,
                'success': True,
            }
        except subprocess.TimeoutExpired as e:
            return {
                'stdout': e.stdout.decode() if e.stdout else '',
                'stderr': e.stderr.decode() if e.stderr else '',
                'return_code': -1,
                'timed_out': True,
                'success': False,
            }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': str(e),
                'return_code': -1,
                'timed_out': False,
                'success': False,
            }


def get_runner(settings: RunnerSettings) -> Runner:
    """Get the appropriate runner for the configured backend."""
    runners = {
        RunnerBackend.LOCAL: LocalRunner,
        RunnerBackend.DOCKER: DockerRunner,
    }

    runner_class = runners.get(settings.backend, LocalRunner)
    return runner_class(settings)
