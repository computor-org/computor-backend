"""
Base executor for interpreted languages (Python, R, Julia, Octave).

Provides common functionality for executing scripts in subprocess,
extracting variables via JSON serialization, and handling I/O.
"""

import json
import os
import subprocess
import tempfile
import time
from abc import abstractmethod
from typing import Any, Dict, List, Optional

from .base import BaseExecutor, ExecutorResult
from .environment import get_safe_env
from .exceptions import ExecutionError, ExecutionTimeoutError
from .resources import make_preexec_fn


class InterpretedExecutor(BaseExecutor):
    """
    Base class for interpreted language executors.

    Handles common patterns for:
    - Running scripts in a subprocess
    - Extracting variables via JSON serialization
    - Capturing stdout/stderr
    - Handling stdin input
    - Setup/teardown code execution

    Subclasses must implement:
    - _get_interpreter_command(): Return the command to run scripts
    - _build_wrapper_script(): Build language-specific wrapper code
    """

    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
        use_safe_env: bool = True,
        check_runtime: bool = True,
        resource_limits=None,
    ):
        super().__init__(working_dir, timeout, use_safe_env, check_runtime, resource_limits=resource_limits)
        self._temp_files: List[str] = []

    @abstractmethod
    def _get_interpreter_command(self) -> List[str]:
        """
        Get the command to invoke the interpreter.

        Returns:
            List of command parts, e.g., ["python3"] or ["Rscript"]
        """
        pass

    @abstractmethod
    def _build_wrapper_script(
        self,
        script_path: str,
        variables_to_extract: List[str],
        setup_code: List[str],
        teardown_code: List[str],
        input_data: Optional[str],
        result_path: str,
    ) -> str:
        """
        Build a wrapper script for the target language.

        The wrapper should:
        1. Execute setup_code (if any)
        2. Execute the main script
        3. Execute teardown_code (if any)
        4. Extract requested variables
        5. Write results to result_path as JSON

        Args:
            script_path: Path to the script to execute
            variables_to_extract: Variable names to extract from namespace
            setup_code: Code lines to run before main script
            teardown_code: Code lines to run after main script
            input_data: Data to provide as stdin
            result_path: Path to write JSON results

        Returns:
            Complete wrapper script code as string
        """
        pass

    def _get_wrapper_extension(self) -> str:
        """Get file extension for wrapper scripts (override in subclass)."""
        return ".tmp"

    def execute(
        self,
        source_path: str,
        variables_to_extract: Optional[List[str]] = None,
        setup_code: Optional[List[str]] = None,
        teardown_code: Optional[List[str]] = None,
        input_data: Optional[str] = None,
    ) -> ExecutorResult:
        """
        Execute a script and extract variables.

        Args:
            source_path: Path to the script file
            variables_to_extract: List of variable names to extract
            setup_code: Code to run before the script
            teardown_code: Code to run after the script
            input_data: Data to send to stdin

        Returns:
            ExecutorResult with execution outcome and extracted variables
        """
        variables_to_extract = variables_to_extract or []
        setup_code = setup_code or []
        teardown_code = teardown_code or []

        # Resolve source path
        if source_path:
            if not os.path.isabs(source_path):
                source_path = os.path.join(self.working_dir, source_path)

            if not os.path.exists(source_path):
                return ExecutorResult(
                    success=False,
                    error_message=f"Source file not found: {source_path}",
                    error_type="FileNotFoundError",
                )
        else:
            source_path = ""

        # Create temp files
        wrapper_path = None
        result_path = None

        try:
            # Create result file path
            result_fd, result_path = tempfile.mkstemp(suffix=".json")
            os.close(result_fd)
            self._temp_files.append(result_path)

            # Create wrapper script
            ext = self._get_wrapper_extension()
            wrapper_fd, wrapper_path = tempfile.mkstemp(suffix=ext)
            self._temp_files.append(wrapper_path)

            wrapper_code = self._build_wrapper_script(
                script_path=source_path,
                variables_to_extract=variables_to_extract,
                setup_code=setup_code,
                teardown_code=teardown_code,
                input_data=input_data,
                result_path=result_path,
            )
            with os.fdopen(wrapper_fd, "w") as f:
                f.write(wrapper_code)

            # Execute in subprocess
            cmd = self._get_interpreter_command() + [wrapper_path]
            env = self._get_env()
            preexec_fn = make_preexec_fn(self.resource_limits) if self.resource_limits else None

            start_time = time.perf_counter()
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=self.working_dir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=env,
                    input=input_data,
                    preexec_fn=preexec_fn,
                )
                duration = time.perf_counter() - start_time
                timed_out = False
                return_code = proc.returncode

            except subprocess.TimeoutExpired as e:
                duration = time.perf_counter() - start_time
                return ExecutorResult(
                    success=False,
                    stdout=e.stdout or "" if hasattr(e, "stdout") else "",
                    stderr=e.stderr or "" if hasattr(e, "stderr") else "",
                    duration=duration,
                    timed_out=True,
                    error_message=f"Execution timed out after {self.timeout}s",
                    error_type="TimeoutError",
                )

            # Read results from JSON file
            result_data = self._read_result_file(result_path)

            # Build ExecutorResult
            return ExecutorResult(
                success=result_data.get("status") == "COMPLETED",
                stdout=result_data.get("stdout", proc.stdout),
                stderr=result_data.get("stderr", proc.stderr),
                duration=result_data.get("exectime", duration),
                return_code=return_code,
                namespace=result_data.get("variables", {}),
                error_message="; ".join(result_data.get("errors", [])),
                error_type=result_data.get("traceback", {}).get("error", "") if isinstance(result_data.get("traceback"), dict) else "",
            )

        except Exception as e:
            return ExecutorResult(
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
            )

        finally:
            self._cleanup_temp_files()

    def _read_result_file(self, result_path: str) -> Dict[str, Any]:
        """Read and parse the JSON result file."""
        try:
            if os.path.exists(result_path):
                with open(result_path, "r") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return {}

    def _cleanup_temp_files(self) -> None:
        """Remove temporary files created during execution."""
        for path in self._temp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except OSError:
                pass
        self._temp_files.clear()

    def cleanup(self) -> None:
        """Clean up resources."""
        self._cleanup_temp_files()
        super().cleanup()

    @staticmethod
    def escape_string(s: str, quote: str = "'") -> str:
        """
        Escape a string for safe inclusion in generated code.

        Args:
            s: String to escape
            quote: Quote character being used

        Returns:
            Escaped string (without surrounding quotes)
        """
        return (s.replace("\\", "\\\\")
                 .replace(quote, f"\\{quote}")
                 .replace("\n", "\\n")
                 .replace("\r", "\\r")
                 .replace("\t", "\\t"))

    @staticmethod
    def escape_path(path: str) -> str:
        """Escape a file path for inclusion in generated code."""
        return InterpretedExecutor.escape_string(path)
