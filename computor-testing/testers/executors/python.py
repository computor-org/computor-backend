"""
Python Code Executor

Handles execution of Python scripts and extraction of variables.

SECURITY: This module uses subprocess execution instead of in-process
exec() to provide isolation between the testing framework and student code.
"""

import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ctexec import InterpretedExecutor, ExecutorResult
from ctexec.exceptions import ExecutionError

# Import the AST-based deny-list. Student code goes through it before
# being executed; reference (lecturer-authored) code is exempt. We use
# ``check_dangerous_imports`` rather than ``analyze_python_security``
# because the latter also flags ``open()`` and ``input()`` as dangerous
# builtins — too noisy for student code that's just doing normal file
# I/O on its own files (which Layer 1 filesystem isolation will keep
# scoped to the student dir anyway).
try:
    from sandbox.security import check_dangerous_imports
    SANDBOX_AVAILABLE = True
except ImportError:
    SANDBOX_AVAILABLE = False


class PyExecutionError(ExecutionError):
    """Exception raised when Python execution fails."""
    pass


def _security_check_disabled_via_env() -> bool:
    """Course-level escape hatch.

    Some curricula legitimately teach ``os`` / ``pathlib`` / file I/O
    and need the deny-list off everywhere. Set
    ``COMPUTOR_TESTING_DISABLE_SECURITY_CHECK=1`` in the test runner's
    environment to disable. Empty / unset / "0" / "false" leave the
    default (on) untouched.
    """
    val = os.environ.get("COMPUTOR_TESTING_DISABLE_SECURITY_CHECK", "").strip().lower()
    return val in {"1", "true", "yes", "on"}


class PyExecutor(InterpretedExecutor):
    """
    Executes Python code and extracts variables.

    Runs Python scripts in an isolated subprocess with configurable timeout.

    Security features:
    - Subprocess isolation (not in-process exec)
    - Clean environment (no secrets passed)
    - Resource limits (CPU, memory, processes)
    - Optional security pre-check for dangerous imports
    """

    language = "python"

    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
        use_sandbox: bool = True,
        security_check: bool = True,
        check_runtime: bool = False,  # Python is always available
    ):
        """Initialize the Python executor.

        Args:
            working_dir: Working directory for Python execution
            timeout: Timeout in seconds
            use_sandbox: Use sandboxed execution (recommended)
            security_check: Pre-check student code for dangerous patterns
                (default True). Pass ``False`` for trusted code paths
                (e.g. running the reference solution where the
                instructor authored the script). The
                ``COMPUTOR_TESTING_DISABLE_SECURITY_CHECK=1`` env var
                disables it globally — for course-wide opt-out where
                the curriculum legitimately requires ``os``/``pathlib``
                etc.
            check_runtime: Check if Python runtime is available
        """
        super().__init__(working_dir, timeout, use_safe_env=True, check_runtime=check_runtime)
        self.use_sandbox = use_sandbox and SANDBOX_AVAILABLE
        self.security_check = security_check and not _security_check_disabled_via_env()

    def _get_interpreter_command(self) -> List[str]:
        """
        Get the Python interpreter command.

        Uses PYTHON_TEST_EXECUTABLE environment variable if set,
        otherwise falls back to sys.executable (framework's Python).
        """
        python_exe = os.environ.get("PYTHON_TEST_EXECUTABLE", sys.executable)
        return [python_exe]

    def _get_wrapper_extension(self) -> str:
        """Get file extension for wrapper scripts."""
        return ".py"

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
        Build a wrapper script that executes the student code and extracts variables.

        This wrapper runs in a subprocess and communicates results via JSON file.
        """
        escaped_script = self.escape_path(script_path)
        escaped_result = self.escape_path(result_path)
        escaped_workdir = self.escape_path(self.working_dir)

        lines = [
            "#!/usr/bin/env python3",
            "# Auto-generated wrapper for safe execution",
            "import sys",
            "import os",
            "import io",
            "import json",
            "import time",
            "import random",
            "import traceback",
            "",
            "# Set random seed for reproducibility",
            "random.seed(1)",
            "try:",
            "    import numpy as np",
            "    np.random.seed(1)",
            "except ImportError:",
            "    pass",
            "",
            "# Change to working directory",
            f"os.chdir('{escaped_workdir}')",
            f"sys.path.insert(0, '{escaped_workdir}')",
            "",
            "# Initialize result",
            "result = {",
            "    'status': 'COMPLETED',",
            "    'errors': [],",
            "    'warnings': [],",
            "    'variables': {},",
            "    'stdout': '',",
            "    'stderr': '',",
            "    'traceback': {},",
            "    'exectime': 0,",
            "}",
            "",
            "# Capture output",
            "stdout_capture = io.StringIO()",
            "stderr_capture = io.StringIO()",
            "",
        ]

        # Set up input if provided
        if input_data:
            escaped_input = self.escape_string(input_data)
            lines.extend([
                f"sys.stdin = io.StringIO('{escaped_input}')",
                "",
            ])

        lines.extend([
            "# Execute the script",
            f"namespace = {{'__file__': '{escaped_script}'}}",
            "start_time = time.time()",
            "",
            "try:",
            "    # Redirect output",
            "    old_stdout = sys.stdout",
            "    old_stderr = sys.stderr",
            "    sys.stdout = stdout_capture",
            "    sys.stderr = stderr_capture",
            "",
        ])

        lines.extend([
            "    # Execute main script first (to get imports into namespace)",
            f"    with open('{escaped_script}', 'r') as f:",
            "        code = f.read()",
            f"    exec(compile(code, '{escaped_script}', 'exec'), namespace)",
            "",
        ])

        # Add setup code AFTER main script (so imports like 'np' are available)
        if setup_code:
            lines.append("    # Setup code (runs after script, has access to imports)")
            for code in setup_code:
                escaped = self.escape_string(code)
                lines.append(f"    exec('{escaped}', namespace)")
            lines.append("")

        # Add teardown code
        if teardown_code:
            lines.append("    # Teardown code")
            for code in teardown_code:
                escaped = self.escape_string(code)
                lines.append(f"    exec('{escaped}', namespace)")
            lines.append("")

        lines.extend([
            "except Exception as e:",
            "    result['status'] = 'FAILED'",
            "    result['errors'].append(str(e))",
            "    tb = traceback.extract_tb(e.__traceback__)",
            "    if tb:",
            "        last = tb[-1]",
            "        result['traceback'] = {",
            "            'name': last.name,",
            "            'filename': last.filename,",
            "            'lineno': last.lineno,",
            "            'line': last.line,",
            "            'error': str(e),",
            "        }",
            "",
            "finally:",
            "    sys.stdout = old_stdout",
            "    sys.stderr = old_stderr",
            "    result['exectime'] = time.time() - start_time",
            "    result['stdout'] = stdout_capture.getvalue()",
            "    result['stderr'] = stderr_capture.getvalue()",
            "",
        ])

        # Extract variables
        if variables_to_extract:
            lines.append("# Extract requested variables")
            lines.append("def serialize_value(val):")
            lines.append("    '''Serialize a value for JSON.'''")
            lines.append("    # Handle complex numbers (Python and numpy)")
            lines.append("    if isinstance(val, complex):")
            lines.append("        return {'__type__': 'complex', '__real__': val.real, '__imag__': val.imag}")
            lines.append("    try:")
            lines.append("        import numpy as np")
            lines.append("        if isinstance(val, np.complexfloating):")
            lines.append("            return {'__type__': 'complex', '__real__': float(val.real), '__imag__': float(val.imag)}")
            lines.append("        if isinstance(val, np.ndarray):")
            lines.append("            # Recursively serialize array data to handle complex elements")
            lines.append("            data = [serialize_value(x) for x in val.flatten().tolist()]")
            lines.append("            return {'__type__': 'ndarray', '__shape__': list(val.shape), '__dtype__': str(val.dtype), '__data__': data}")
            lines.append("        if isinstance(val, (np.integer, np.floating)):")
            lines.append("            return float(val)")
            lines.append("        if isinstance(val, np.bool_):")
            lines.append("            return bool(val)")
            lines.append("    except:")
            lines.append("        pass")
            lines.append("    if isinstance(val, (list, tuple)):")
            lines.append("        return [serialize_value(x) for x in val]")
            lines.append("    if isinstance(val, dict):")
            lines.append("        return {k: serialize_value(v) for k, v in val.items()}")
            lines.append("    if isinstance(val, (int, float, str, bool, type(None))):")
            lines.append("        return val")
            lines.append("    return repr(val)")
            lines.append("")

            for var in variables_to_extract:
                escaped_var = self.escape_string(var)
                lines.extend([
                    f"try:",
                    f"    # Try direct lookup first, then eval for expressions",
                    f"    if '{escaped_var}' in namespace:",
                    f"        result['variables']['{escaped_var}'] = serialize_value(namespace['{escaped_var}'])",
                    f"    else:",
                    f"        result['variables']['{escaped_var}'] = serialize_value(eval('{escaped_var}', namespace))",
                    f"except Exception:",
                    f"    pass  # Variable or expression not found",
                ])
            lines.append("")

        lines.extend([
            "# Write result to file",
            f"with open('{escaped_result}', 'w') as f:",
            "    json.dump(result, f)",
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
        Execute a Python script and extract variables.

        This is the legacy interface for backwards compatibility.
        New code should use execute() instead.

        Args:
            script_path: Path to the Python script
            variables_to_extract: List of variable names to extract
            setup_code: Code to run before the script
            teardown_code: Code to run after the script
            input_answers: Input values for interactive prompts

        Returns:
            Dictionary with execution results and extracted variables
        """
        # Security pre-check: AST-based deny-list for dangerous imports.
        # Closes the "import os; open('../reference/solution.py')" exploit
        # at the source. Defense in depth — Layer 1 filesystem isolation
        # is the real fix, but this catches obvious attempts before they
        # ever reach the subprocess.
        if self.security_check and SANDBOX_AVAILABLE:
            full_path = (
                script_path
                if os.path.isabs(script_path)
                else os.path.join(self.working_dir, script_path)
            )
            try:
                with open(full_path, 'r') as f:
                    code = f.read()
                issues = check_dangerous_imports(code)
                if issues:
                    return {
                        "status": "BLOCKED",
                        "errors": [f"Security check failed: {i.message}"
                                   for i in issues[:5]],
                        "warnings": [],
                        "variables": {},
                        "stdout": "",
                        "stderr": "",
                        "traceback": {},
                        "exectime": 0,
                    }
            except (OSError, UnicodeDecodeError):
                # Can't read the script — let the executor surface the
                # error its own way rather than silently passing it.
                pass

        # Convert input_answers list to string
        input_data = None
        if input_answers:
            input_data = "\n".join(input_answers)

        # Use parent class execute()
        result = self.execute(
            source_path=script_path,
            variables_to_extract=variables_to_extract,
            setup_code=setup_code,
            teardown_code=teardown_code,
            input_data=input_data,
        )

        # Deserialize numpy arrays in variables
        if result.namespace:
            result.namespace = self._deserialize_variables(result.namespace)

        # Convert ExecutorResult to legacy dict format
        return {
            "status": "COMPLETED" if result.success else ("TIMEOUT" if result.timed_out else "FAILED"),
            "errors": [result.error_message] if result.error_message else [],
            "warnings": [],
            "variables": result.namespace,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "traceback": {"error": result.error_type} if result.error_type else {},
            "exectime": result.duration,
        }

    def _deserialize_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize variables from JSON format."""
        result = {}
        for name, value in variables.items():
            result[name] = self._deserialize_value(value)
        return result

    def _deserialize_value(self, value: Any) -> Any:
        """Deserialize a single value from JSON format."""
        if isinstance(value, dict):
            if value.get('__type__') == 'complex':
                return complex(value['__real__'], value['__imag__'])
            if value.get('__type__') == 'ndarray':
                # First deserialize the data (may contain complex numbers)
                data = [self._deserialize_value(x) for x in value['__data__']]
                shape = tuple(value['__shape__'])
                dtype = value.get('__dtype__', 'float64')
                arr = np.array(data).reshape(shape)
                # Try to convert to the original dtype
                try:
                    return arr.astype(dtype)
                except (TypeError, ValueError):
                    return arr
            return {k: self._deserialize_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._deserialize_value(x) for x in value]
        return value

    def get_variable(self, var_name: str, script_path: str) -> Tuple[Any, Optional[str]]:
        """
        Execute a script and get a specific variable.

        Args:
            var_name: Name of the variable to extract
            script_path: Path to the Python script

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


def check_python_installed() -> Tuple[bool, str]:
    """
    Check Python version info.

    Returns:
        Tuple of (is_installed, version_info)
    """
    return PyExecutor.check_installed()
