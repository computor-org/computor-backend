"""
R Code Executor

Handles execution of R scripts and extraction of variables.

SECURITY: This module uses safe environment handling to prevent
leaking secrets to R processes.
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


class RExecutionError(ExecutionError):
    """Exception raised when R execution fails."""
    pass


class RExecutor(InterpretedExecutor):
    """
    Executes R code and extracts variables.

    Uses Rscript for non-interactive execution and JSON for data exchange.
    """

    language = "r"

    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
        check_runtime: bool = True,
    ):
        """
        Initialize the R executor.

        Args:
            working_dir: Working directory for R execution
            timeout: Timeout in seconds for R execution
            check_runtime: Check if R runtime is available
        """
        super().__init__(working_dir, timeout, use_safe_env=True, check_runtime=check_runtime)

    def _get_interpreter_command(self) -> List[str]:
        """Get the R interpreter command."""
        return ["Rscript", "--vanilla"]

    def _get_wrapper_extension(self) -> str:
        """Get file extension for wrapper scripts."""
        return ".R"

    def _get_env(self, extra_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Get environment variables for R execution."""
        env = super()._get_env(extra_vars)
        # R needs HOME and may need R_LIBS_USER
        env['HOME'] = os.path.expanduser('~')
        # Pass through R library path if set
        if 'R_LIBS_USER' in os.environ:
            env['R_LIBS_USER'] = os.environ['R_LIBS_USER']
        if 'R_LIBS' in os.environ:
            env['R_LIBS'] = os.environ['R_LIBS']
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
        """Build the R code for execution with variable extraction."""
        escaped_script = self.escape_path(script_path)
        escaped_result = self.escape_path(result_path)

        lines = [
            "# Auto-generated R execution wrapper",
            "# Add user library path",
            ".libPaths(c(Sys.getenv('R_LIBS_USER'), .libPaths()))",
            "library(jsonlite)",
            "",
            "# Capture warnings and errors",
            "warnings_list <- list()",
            "errors_list <- list()",
            "traceback_info <- list()",
            "",
            "# Capture stdout",
            "stdout_capture <- ''",
            "",
            "tryCatch({",
        ]

        # Add setup code
        if setup_code:
            lines.append("  # Setup code")
            for code in setup_code:
                lines.append(f"  {code}")
            lines.append("")

        # Source the main script
        lines.extend([
            f"  # Execute main script",
            f"  source('{escaped_script}')",
            "",
        ])

        # Add teardown code
        if teardown_code:
            lines.append("  # Teardown code")
            for code in teardown_code:
                lines.append(f"  {code}")
            lines.append("")

        lines.extend([
            "}, warning = function(w) {",
            "  warnings_list <<- c(warnings_list, conditionMessage(w))",
            "  invokeRestart('muffleWarning')",
            "}, error = function(e) {",
            "  errors_list <<- c(errors_list, conditionMessage(e))",
            "  traceback_info <<- list(error = conditionMessage(e))",
            "})",
            "",
        ])

        # Extract variables
        if variables_to_extract:
            lines.extend([
                "# Extract variables",
                "extracted_vars <- list()",
            ])

            for var in variables_to_extract:
                escaped_var = var.replace("'", "\\'")
                lines.extend([
                    f"if (exists('{escaped_var}')) {{",
                    f"  extracted_vars${var} <- get('{escaped_var}')",
                    "}",
                ])

            lines.append("")

        # Output results as JSON to file
        lines.extend([
            "# Output results to file",
            "result <- list(",
            "  status = if (length(errors_list) == 0) 'COMPLETED' else 'FAILED',",
            "  errors = errors_list,",
            "  warnings = warnings_list,",
            f"  variables = {'extracted_vars' if variables_to_extract else 'list()'},",
            "  traceback = traceback_info",
            ")",
            "",
            f"write(toJSON(result, auto_unbox = TRUE, digits = 15), '{escaped_result}')",
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
        Execute an R script and extract variables.

        This is the legacy interface for backwards compatibility.
        New code should use execute() instead.

        Args:
            script_path: Path to the R script
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

        # Convert R values in namespace
        if result.namespace:
            result.namespace = self._convert_r_values(result.namespace)

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

    def _convert_r_values(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Convert R values to Python/numpy types."""
        converted = {}
        for name, value in variables.items():
            converted[name] = self._convert_value(value)
        return converted

    def _convert_value(self, value: Any) -> Any:
        """Convert a single R value to Python type."""
        if value is None:
            return None

        if isinstance(value, list):
            # R vectors become numpy arrays
            if len(value) > 0 and all(isinstance(x, (int, float)) for x in value):
                return np.array(value)
            # R lists stay as lists (possibly nested)
            return [self._convert_value(x) for x in value]

        if isinstance(value, dict):
            # R named lists/data frames
            return {k: self._convert_value(v) for k, v in value.items()}

        return value

    def get_variable(self, var_name: str, script_path: str) -> Tuple[Any, Optional[str]]:
        """
        Execute a script and get a specific variable.

        Args:
            var_name: Name of the variable to extract
            script_path: Path to the R script

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


def check_r_installed() -> Tuple[bool, str]:
    """
    Check if R is installed and available.

    Returns:
        Tuple of (is_installed, version_or_error)
    """
    return RExecutor.check_installed()
