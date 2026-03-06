"""
Julia Code Executor

Handles execution of Julia scripts and extraction of variables.

SECURITY: This module uses safe environment handling to prevent
leaking secrets to Julia processes.
"""

import json
import os
import sys
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ctexec import InterpretedExecutor, ExecutorResult
from ctexec.exceptions import ExecutionError
from ctexec.environment import BLOCKED_ENV_VARS


class JuliaExecutionError(ExecutionError):
    """Exception raised when Julia execution fails."""
    pass


def find_julia_binary() -> str:
    """Find Julia binary in common locations."""
    import shutil

    # First try PATH
    julia_path = shutil.which("julia")
    if julia_path:
        return julia_path

    # Common installation locations
    home = os.path.expanduser("~")
    common_paths = [
        os.path.join(home, ".juliaup", "bin", "julia"),
        os.path.join(home, ".julia", "bin", "julia"),
        "/usr/local/bin/julia",
        "/usr/bin/julia",
        "/snap/bin/julia",
        "/opt/julia/bin/julia",
    ]

    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    return "julia"  # Fall back to hoping it's in PATH


# Cache the Julia binary path
JULIA_BINARY = find_julia_binary()


class JuliaExecutor(InterpretedExecutor):
    """
    Executes Julia code and extracts variables.

    Uses julia for non-interactive execution and JSON for data exchange.
    """

    language = "julia"

    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
        check_runtime: bool = True,
    ):
        """
        Initialize the Julia executor.

        Args:
            working_dir: Working directory for Julia execution
            timeout: Timeout in seconds for Julia execution
            check_runtime: Check if Julia runtime is available
        """
        super().__init__(working_dir, timeout, use_safe_env=True, check_runtime=check_runtime)

    def _get_interpreter_command(self) -> List[str]:
        """Get the Julia interpreter command."""
        return [JULIA_BINARY, "--startup-file=no"]

    def _get_wrapper_extension(self) -> str:
        """Get file extension for wrapper scripts."""
        return ".jl"

    def _get_env(self, extra_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get environment variables for Julia execution.

        Note: Julia needs a fuller environment than other languages
        due to juliaup launcher requirements.
        """
        # Julia needs most of the environment, just filter sensitive vars
        env = os.environ.copy()
        for var in BLOCKED_ENV_VARS:
            env.pop(var, None)
        if extra_vars:
            env.update(extra_vars)
        return env

    def _build_wrapper_script(
        self,
        script_path: str,
        variables_to_extract: List[str],
        setup_code: List[str],
        teardown_code: List[str],
        input_data: Optional[str],
        result_path: str,
    ) -> str:
        """Build the Julia code for execution with variable extraction."""
        escaped_script = self.escape_path(script_path)
        escaped_result = self.escape_path(result_path)

        lines = [
            "# Auto-generated Julia execution wrapper",
            "using JSON",
            "",
            "# Capture warnings and errors",
            "warnings_list = String[]",
            "errors_list = String[]",
            "execution_status = \"COMPLETED\"",
            "traceback_info = Dict{String, Any}()",
            "",
        ]

        # Add setup code
        if setup_code:
            lines.append("# Setup code")
            for code in setup_code:
                lines.append(code)
            lines.append("")

        # Execute the main script with error handling
        lines.extend([
            "# Execute main script",
            "try",
            f'    include("{escaped_script}")',
            "catch e",
            '    global execution_status = "FAILED"',
            "    push!(errors_list, sprint(showerror, e))",
            '    traceback_info["error"] = sprint(showerror, e)',
            "end",
            "",
        ])

        # Add teardown code
        if teardown_code:
            lines.append("# Teardown code")
            for code in teardown_code:
                lines.append(code)
            lines.append("")

        # Extract variables
        lines.extend([
            "# Extract variables",
            "extracted_vars = Dict{String, Any}()",
        ])

        for var in variables_to_extract:
            escaped_var = var.replace('"', '\\"')
            lines.extend([
                f'if @isdefined({var})',
                f'    extracted_vars["{escaped_var}"] = {var}',
                "end",
            ])

        lines.append("")

        # Output results as JSON to file
        lines.extend([
            "# Output results to file",
            "result = Dict(",
            '    "status" => execution_status,',
            '    "errors" => errors_list,',
            '    "warnings" => warnings_list,',
            '    "variables" => extracted_vars,',
            '    "traceback" => traceback_info',
            ")",
            "",
            f'open("{escaped_result}", "w") do f',
            "    JSON.print(f, result)",
            "end",
        ])

        return "\n".join(lines)

    def execute_script(
        self,
        script_path: str,
        variables_to_extract: Optional[List[str]] = None,
        setup_code: Optional[List[str]] = None,
        teardown_code: Optional[List[str]] = None,
        input_answers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a Julia script and extract variables.

        This is the legacy interface for backwards compatibility.
        New code should use execute() instead.

        Args:
            script_path: Path to the Julia script
            variables_to_extract: List of variable names to extract
            setup_code: Code to run before the script
            teardown_code: Code to run after the script
            input_answers: Input values for interactive prompts

        Returns:
            Dictionary with execution results and extracted variables
        """
        variables_to_extract = variables_to_extract or []
        setup_code = setup_code or []
        teardown_code = teardown_code or []

        # Convert input_answers to input_data string
        input_data = "\n".join(input_answers) if input_answers else None

        # Use parent class execute()
        result = self.execute(
            source_path=script_path,
            variables_to_extract=variables_to_extract,
            setup_code=setup_code,
            teardown_code=teardown_code,
            input_data=input_data,
        )

        # Convert Julia values in namespace
        if result.namespace:
            result.namespace = self._convert_julia_values(result.namespace)

        # Convert ExecutorResult to legacy dict format
        return {
            "status": "COMPLETED" if result.success else ("TIMEOUT" if result.timed_out else "FAILED"),
            "errors": [result.error_message] if result.error_message else [],
            "warnings": [],
            "variables": result.namespace,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.return_code,
        }

    def _convert_julia_values(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Julia values to Python/numpy types."""
        converted = {}
        for name, value in variables.items():
            converted[name] = self._convert_value(value)
        return converted

    def _convert_value(self, value: Any) -> Any:
        """Convert a single Julia value to Python type."""
        if value is None:
            return None

        if isinstance(value, list):
            # Julia vectors become numpy arrays
            if len(value) > 0 and all(isinstance(x, (int, float)) for x in value):
                return np.array(value)
            # Julia arrays stay as lists (possibly nested)
            return [self._convert_value(x) for x in value]

        if isinstance(value, dict):
            # Julia Dicts/named tuples
            return {k: self._convert_value(v) for k, v in value.items()}

        return value

    def get_variable(self, var_name: str, script_path: str) -> Tuple[Any, Optional[str]]:
        """
        Execute a script and get a specific variable.

        Args:
            var_name: Name of the variable to extract
            script_path: Path to the Julia script

        Returns:
            Tuple of (value, error_message)
        """
        result = self.execute_script(script_path, variables_to_extract=[var_name])

        if result["status"] != "COMPLETED":
            errors = result.get("errors", ["Unknown error"])
            return None, "; ".join(str(e) for e in errors)

        variables = result.get("variables", {})
        if var_name not in variables:
            return None, f"Variable '{var_name}' not found"

        return variables[var_name], None


def check_julia_installed() -> Tuple[bool, str]:
    """
    Check if Julia is installed and available.

    Returns:
        Tuple of (is_installed, version_or_error)
    """
    return JuliaExecutor.check_installed()
