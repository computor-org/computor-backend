"""
Base executor for compiled languages (C, C++, Fortran).

Provides common functionality for compiling source files,
running executables, and capturing stdout/stderr.
"""

import os
import shutil
import subprocess
import tempfile
import time
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import BaseExecutor, ExecutorResult
from .environment import get_safe_env, filter_env
from .exceptions import CompilationError, ExecutionError, ExecutionTimeoutError
from .resources import make_preexec_fn


@dataclass
class CompilationResult:
    """Result of a compilation attempt."""

    success: bool
    executable_path: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    duration: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.success


class CompiledExecutor(BaseExecutor):
    """
    Base class for compiled language executors (C, C++, Fortran).

    Handles common patterns for:
    - Compiling source files to executables
    - Running executables with stdin/stdout capture
    - Managing temporary directories
    - Clean environment execution

    Subclasses must implement:
    - _get_default_compiler(): Return the default compiler command
    - _get_default_flags(): Return default compiler flags
    - _detect_language(): Detect language from source files (if needed)
    """

    default_compile_timeout: float = 60.0
    default_run_timeout: float = 30.0

    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
        compile_timeout: Optional[float] = None,
        use_safe_env: bool = True,
        check_runtime: bool = True,
        resource_limits=None,
    ):
        """
        Initialize the compiled language executor.

        Args:
            working_dir: Directory containing source files
            timeout: Run timeout in seconds (default: 30)
            compile_timeout: Compilation timeout in seconds (default: 60)
            use_safe_env: Use safe environment variables
            check_runtime: Check if compiler is available on init
            resource_limits: Optional resource limits (CPU, memory, etc.)
        """
        # Set run timeout as the main timeout
        if timeout is None:
            timeout = self.default_run_timeout
        super().__init__(working_dir, timeout, use_safe_env, check_runtime, resource_limits=resource_limits)

        self.compile_timeout = (
            compile_timeout
            if compile_timeout is not None
            else self.default_compile_timeout
        )

        # State
        self.temp_dir: Optional[str] = None
        self.executable_path: Optional[str] = None
        self.last_compilation: Optional[CompilationResult] = None

    @abstractmethod
    def _get_default_compiler(self) -> str:
        """
        Get the default compiler command.

        Returns:
            Compiler command, e.g., "gcc" or "gfortran"
        """
        pass

    @abstractmethod
    def _get_default_flags(self) -> List[str]:
        """
        Get default compiler flags.

        Returns:
            List of compiler flags, e.g., ["-Wall", "-Wextra"]
        """
        pass

    def _parse_compiler_output(self, stderr: str) -> tuple:
        """
        Parse compiler output into warnings and errors.

        Args:
            stderr: Compiler stderr output

        Returns:
            Tuple of (warnings_list, errors_list)
        """
        warnings = []
        errors = []
        for line in stderr.split("\n"):
            line_lower = line.lower()
            if "warning:" in line_lower:
                warnings.append(line)
            elif "error:" in line_lower:
                errors.append(line)
        return warnings, errors

    def compile(
        self,
        source_files: List[str],
        compiler: Optional[str] = None,
        flags: Optional[List[str]] = None,
        linker_flags: Optional[List[str]] = None,
        output_name: Optional[str] = None,
    ) -> CompilationResult:
        """
        Compile source files to an executable.

        Args:
            source_files: List of source files (relative to working_dir)
            compiler: Override default compiler
            flags: Override default compiler flags
            linker_flags: Additional linker flags
            output_name: Output executable name (default: "a.out")

        Returns:
            CompilationResult with success status and details
        """
        if not source_files:
            return CompilationResult(
                success=False, stderr="No source files specified", return_code=-1
            )

        # Resolve source paths
        resolved = []
        for src in source_files:
            path = src if os.path.isabs(src) else os.path.join(self.working_dir, src)
            if not os.path.exists(path):
                return CompilationResult(
                    success=False,
                    stderr=f"Source file not found: {path}",
                    return_code=-1,
                )
            resolved.append(path)

        # Set up temp directory
        self.temp_dir = tempfile.mkdtemp(prefix=f"{self.language}exec_")
        self.executable_path = os.path.join(self.temp_dir, output_name or "a.out")

        # Build compiler command
        actual_compiler = compiler or self._get_default_compiler()
        actual_flags = flags if flags is not None else self._get_default_flags()

        cmd = [actual_compiler]
        cmd.extend(actual_flags)
        cmd.extend(resolved)
        cmd.extend(["-o", self.executable_path])
        if linker_flags:
            cmd.extend(linker_flags)

        # Run compilation
        start_time = time.perf_counter()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=self.compile_timeout,
            )
            duration = time.perf_counter() - start_time

            warnings, errors = self._parse_compiler_output(result.stderr)

            self.last_compilation = CompilationResult(
                success=(result.returncode == 0),
                executable_path=self.executable_path if result.returncode == 0 else None,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                duration=duration,
                warnings=warnings,
                errors=errors,
            )

        except subprocess.TimeoutExpired:
            duration = time.perf_counter() - start_time
            self.last_compilation = CompilationResult(
                success=False,
                stderr=f"Compilation timed out after {self.compile_timeout}s",
                return_code=-1,
                duration=duration,
            )

        except FileNotFoundError:
            self.last_compilation = CompilationResult(
                success=False,
                stderr=f"Compiler not found: {actual_compiler}",
                return_code=-1,
            )

        except Exception as e:
            self.last_compilation = CompilationResult(
                success=False, stderr=f"Compilation error: {str(e)}", return_code=-1
            )

        return self.last_compilation

    def run(
        self,
        args: Optional[List[str]] = None,
        stdin: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> ExecutorResult:
        """
        Run the compiled executable.

        Args:
            args: Command line arguments for the executable
            stdin: Input to send to stdin
            timeout: Override default run timeout

        Returns:
            ExecutorResult with stdout, stderr, and exit code
        """
        if not self.executable_path or not os.path.exists(self.executable_path):
            return ExecutorResult(
                success=False,
                error_message="No executable available. Compile first.",
                error_type="RuntimeError",
            )

        cmd = [self.executable_path]
        if args:
            cmd.extend(args)

        env = self._get_env()
        actual_timeout = timeout or self.timeout
        preexec_fn = make_preexec_fn(self.resource_limits) if self.resource_limits else None

        start_time = time.perf_counter()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=actual_timeout,
                env=env,
                preexec_fn=preexec_fn,
            )
            duration = time.perf_counter() - start_time

            return ExecutorResult(
                success=True,  # Process completed (may have non-zero exit)
                stdout=result.stdout,
                stderr=result.stderr,
                duration=duration,
                return_code=result.returncode,
            )

        except subprocess.TimeoutExpired as e:
            duration = time.perf_counter() - start_time
            return ExecutorResult(
                success=False,
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=e.stderr.decode() if e.stderr else "",
                duration=duration,
                return_code=-1,
                timed_out=True,
                error_message=f"Execution timed out after {actual_timeout}s",
                error_type="TimeoutError",
            )

        except Exception as e:
            return ExecutorResult(
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
            )

    def compile_and_run(
        self,
        source_files: List[str],
        args: Optional[List[str]] = None,
        stdin: Optional[str] = None,
        compiler: Optional[str] = None,
        flags: Optional[List[str]] = None,
    ) -> ExecutorResult:
        """
        Compile and run in one step.

        Args:
            source_files: List of source files
            args: Arguments for the executable
            stdin: Input for stdin
            compiler: Override compiler
            flags: Override compiler flags

        Returns:
            ExecutorResult (includes compilation info if it failed)
        """
        comp_result = self.compile(source_files, compiler=compiler, flags=flags)

        if not comp_result.success:
            return ExecutorResult(
                success=False,
                compilation_success=False,
                compilation_stdout=comp_result.stdout,
                compilation_stderr=comp_result.stderr,
                compilation_duration=comp_result.duration,
                error_message=f"Compilation failed: {comp_result.stderr[:200]}",
                error_type="CompilationError",
            )

        run_result = self.run(args=args, stdin=stdin)
        # Add compilation info
        run_result.compilation_success = True
        run_result.compilation_stdout = comp_result.stdout
        run_result.compilation_stderr = comp_result.stderr
        run_result.compilation_duration = comp_result.duration
        return run_result

    def execute(
        self,
        source_path: str,
        variables_to_extract: Optional[List[str]] = None,
        setup_code: Optional[List[str]] = None,
        teardown_code: Optional[List[str]] = None,
        input_data: Optional[str] = None,
    ) -> ExecutorResult:
        """
        Execute implementation for BaseExecutor interface.

        For compiled languages, this compiles and runs the source file.
        Note: variables_to_extract, setup_code, teardown_code are ignored
        (compiled languages don't support variable extraction).

        Args:
            source_path: Path to source file
            variables_to_extract: Ignored for compiled languages
            setup_code: Ignored for compiled languages
            teardown_code: Ignored for compiled languages
            input_data: Data to send to stdin

        Returns:
            ExecutorResult with execution outcome
        """
        return self.compile_and_run(
            source_files=[source_path],
            stdin=input_data,
        )

    def cleanup(self) -> None:
        """Clean up temporary files and directories."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except OSError:
                pass
            self.temp_dir = None
            self.executable_path = None
        super().cleanup()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.cleanup()
        return False
