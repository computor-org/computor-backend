"""
Secure Sandbox Executor

Provides sandboxed execution of code with resource limits and isolation.
"""

import os
import sys
import subprocess
import tempfile
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Import canonical resource limit definitions from ctexec
# These are the single source of truth for resource limiting
from ctexec.resources import ResourceLimits, set_resource_limits, make_preexec_fn


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""

    # Resource limits
    limits: ResourceLimits = field(default_factory=ResourceLimits)

    # Environment control
    clean_environment: bool = True
    env_whitelist: List[str] = field(default_factory=list)
    extra_env: Dict[str, str] = field(default_factory=dict)

    # Paths
    writable_paths: List[str] = field(default_factory=list)

    # Behavior
    capture_output: bool = True
    merge_stderr: bool = False


# Import canonical environment definitions from ctexec
# These are the single source of truth for safe env and blocked vars
from ctexec.environment import (
    DEFAULT_SAFE_ENV,
    BLOCKED_ENV_VARS,
)


class SandboxExecutor:
    """
    Execute code in a sandboxed environment.

    Features:
    - Clean environment variables (no secrets)
    - Resource limits (CPU, memory, processes, files)
    - Execution timeout
    - Output capture

    Usage:
        config = SandboxConfig()
        with SandboxExecutor(config) as executor:
            result = executor.run(["python", "student_code.py"], cwd="/sandbox")
    """

    def __init__(self, config: SandboxConfig = None):
        """
        Initialize the sandbox executor.

        Args:
            config: SandboxConfig for execution settings
        """
        self.config = config or SandboxConfig()
        self._temp_dir: Optional[str] = None

    def _get_safe_env(self) -> Dict[str, str]:
        """
        Build a safe environment dictionary.

        Returns:
            Clean environment with no sensitive data
        """
        if not self.config.clean_environment:
            # Use current environment but filter blocked vars
            env = {k: v for k, v in os.environ.items()
                   if k.upper() not in BLOCKED_ENV_VARS
                   and not any(blocked in k.upper() for blocked in
                             ['SECRET', 'PASSWORD', 'TOKEN', 'KEY', 'CREDENTIAL'])}
        else:
            # Start with minimal safe environment
            env = DEFAULT_SAFE_ENV.copy()

        # Add whitelisted vars from actual environment
        for key in self.config.env_whitelist:
            if key in os.environ and key.upper() not in BLOCKED_ENV_VARS:
                env[key] = os.environ[key]

        # Add any extra environment variables
        for key, value in self.config.extra_env.items():
            if key.upper() not in BLOCKED_ENV_VARS:
                env[key] = value

        return env

    def _preexec_fn(self) -> None:
        """Pre-execution function for subprocess."""
        if sys.platform != 'win32':
            set_resource_limits(self.config.limits)

    def run(self, cmd: List[str],
            stdin: Optional[str] = None,
            cwd: Optional[str] = None,
            timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Run a command in the sandbox.

        Args:
            cmd: Command and arguments to execute
            stdin: Input to send to stdin
            cwd: Working directory
            timeout: Override default timeout

        Returns:
            Dictionary with:
                - stdout: captured stdout
                - stderr: captured stderr
                - return_code: process exit code
                - timed_out: whether execution timed out
                - success: True if process completed (regardless of exit code)
        """
        actual_timeout = timeout or self.config.limits.timeout

        try:
            # On Windows, we can't use preexec_fn
            preexec = None if sys.platform == 'win32' else self._preexec_fn

            result = subprocess.run(
                cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=actual_timeout,
                cwd=cwd,
                env=self._get_safe_env(),
                preexec_fn=preexec,
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

    def run_python(self, script_path: str,
                   args: List[str] = None,
                   stdin: Optional[str] = None,
                   cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Run a Python script in the sandbox.

        Args:
            script_path: Path to the Python script
            args: Additional arguments to pass
            stdin: Input for stdin
            cwd: Working directory

        Returns:
            Execution result dictionary
        """
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args)
        return self.run(cmd, stdin=stdin, cwd=cwd)

    def run_octave(self, script_path: str,
                   stdin: Optional[str] = None,
                   cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Run an Octave script in the sandbox.

        Args:
            script_path: Path to the Octave script
            stdin: Input for stdin
            cwd: Working directory

        Returns:
            Execution result dictionary
        """
        cmd = [
            os.environ.get("OCTAVE_EXECUTABLE", "octave"),
            "--no-gui",
            "--no-window-system",
            "--silent",
            script_path
        ]
        return self.run(cmd, stdin=stdin, cwd=cwd)

    def run_r(self, script_path: str,
              stdin: Optional[str] = None,
              cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Run an R script in the sandbox.

        Args:
            script_path: Path to the R script
            stdin: Input for stdin
            cwd: Working directory

        Returns:
            Execution result dictionary
        """
        cmd = ["Rscript", "--vanilla", script_path]
        return self.run(cmd, stdin=stdin, cwd=cwd)

    def compile_and_run_c(self, source_files: List[str],
                          compiler: str = "gcc",
                          compiler_flags: List[str] = None,
                          args: List[str] = None,
                          stdin: Optional[str] = None,
                          cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Compile and run C/C++ code in the sandbox.

        Args:
            source_files: List of source files to compile
            compiler: Compiler to use (gcc, g++, clang)
            compiler_flags: Additional compiler flags
            args: Runtime arguments
            stdin: Input for stdin
            cwd: Working directory

        Returns:
            Dictionary with compilation and execution results
        """
        import tempfile

        # Create temp executable
        with tempfile.NamedTemporaryFile(suffix='', delete=False) as f:
            executable = f.name

        try:
            # Build compile command
            cmd = [compiler]
            if compiler_flags:
                cmd.extend(compiler_flags)
            else:
                cmd.extend(["-Wall", "-Wextra"])
            cmd.extend(source_files)
            cmd.extend(["-o", executable])

            # Compile
            compile_result = self.run(cmd, cwd=cwd)

            if compile_result['return_code'] != 0:
                return {
                    'compilation': compile_result,
                    'execution': None,
                    'success': False,
                }

            # Run
            run_cmd = [executable]
            if args:
                run_cmd.extend(args)

            exec_result = self.run(run_cmd, stdin=stdin, cwd=cwd)

            return {
                'compilation': compile_result,
                'execution': exec_result,
                'success': exec_result['success'],
            }

        finally:
            # Clean up executable
            if os.path.exists(executable):
                try:
                    os.unlink(executable)
                except OSError:
                    pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clean up any temp files if needed
        if self._temp_dir and os.path.exists(self._temp_dir):
            import shutil
            try:
                shutil.rmtree(self._temp_dir)
            except OSError:
                pass
