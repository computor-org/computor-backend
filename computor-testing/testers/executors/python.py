"""
Python Code Executor

Handles execution of Python scripts and extraction of variables.

SECURITY: This module uses subprocess execution instead of in-process
exec() to provide isolation between the testing framework and student code.
"""

import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ctexec.process import max_output_bytes
from ctexec import InterpretedExecutor, ExecutorResult
from ctexec.exceptions import ExecutionError
from ctexec.safe_io import read_untrusted_bytes, read_untrusted_text

# Import sandbox security analysis
try:
    from sandbox.security import analyze_python_security
    SANDBOX_AVAILABLE = True
except ImportError:
    SANDBOX_AVAILABLE = False


class PyExecutionError(ExecutionError):
    """Exception raised when Python execution fails."""
    pass


FIGURE_SUBDIR = "figures"
MAX_FIGURES = 20
_FIGURE_NAME = re.compile(r"figure_\d{1,4}\.png")


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
        security_check: bool = False,
        check_runtime: bool = False,  # Python is always available
        graphics: bool = False,
        figure_dir: Optional[str] = None,
        figure_prefix: str = "",
    ):
        """
        Initialize the Python executor.

        Args:
            working_dir: Working directory for Python execution
            timeout: Timeout in seconds
            use_sandbox: Use sandboxed execution (recommended)
            security_check: Pre-check code for dangerous patterns
            check_runtime: Check if Python runtime is available
        """
        super().__init__(working_dir, timeout, use_safe_env=True, check_runtime=check_runtime)
        self.use_sandbox = use_sandbox and SANDBOX_AVAILABLE
        self.security_check = security_check
        # Graphics tests (#237): evaluated inside the job, never in the
        # harness. `plt` is bound in the job's namespace so `plt.<expr>`
        # names extract like variables; figures are saved into the private
        # result dir and copied out (size-capped, no symlinks) to figure_dir.
        self.graphics = graphics
        self.figure_dir = figure_dir
        self.figure_prefix = figure_prefix

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
            "# Capture output, bounded while it is written (#237): an output",
            "# flood must not grow the job's memory or the result file.",
            "class _BoundedCapture(io.TextIOBase):",
            "    # Keeps at most `limit` UTF-8 bytes; empty writes store nothing.",
            "    def __init__(self, limit):",
            "        self._parts, self._kept, self._limit, self.dropped = [], 0, limit, 0",
            "    def writable(self):",
            "        return True",
            "    def write(self, s):",
            "        if not isinstance(s, str):",
            "            raise TypeError('write() argument must be str')",
            "        if not s:",
            "            return 0",
            "        room = self._limit - self._kept",
            "        kept_chars = 0",
            "        if room > 0:",
            "            # s[:room] holds at least `room` bytes (>= 1 byte per char);",
            "            # cut the encoding to the byte budget, dropping a split char.",
            "            data = s[:room].encode('utf-8', 'replace')[:room]",
            "            data = data.decode('utf-8', 'ignore').encode('utf-8')",
            "            if data:",
            "                self._parts.append(data)",
            "                self._kept += len(data)",
            "                kept_chars = len(data.decode('utf-8'))",
            "            if len(data) < room and kept_chars < len(s):",
            "                self._kept = self._limit  # budget exhausted mid-char",
            "        self.dropped += len(s) - kept_chars",
            "        return len(s)",
            "    def getvalue(self):",
            "        text = b''.join(self._parts).decode('utf-8', 'replace')",
            "        if self.dropped:",
            "            text += '\\n[... output truncated: %d more characters discarded ...]\\n' % self.dropped",
            "        return text",
            f"stdout_capture = _BoundedCapture({max_output_bytes()})",
            f"stderr_capture = _BoundedCapture({max_output_bytes()})",
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

        if self.graphics:
            lines.extend([
                "# Graphics test: expose pyplot for plt.<expr> extraction",
                "try:",
                "    import matplotlib.pyplot as _ct_plt",
                "    namespace['plt'] = _ct_plt",
                "except Exception as e:",
                "    result['warnings'].append('matplotlib unavailable: %s' % e)",
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

        if self.graphics and self.figure_dir:
            escaped_figs = self.escape_path(
                os.path.join(os.path.dirname(result_path), FIGURE_SUBDIR))
            lines.extend([
                "# Save open figures for the harness to collect",
                "try:",
                "    import matplotlib.pyplot as _ct_plt",
                f"    os.makedirs('{escaped_figs}', exist_ok=True)",
                f"    for _ct_n in _ct_plt.get_fignums()[:{MAX_FIGURES}]:",
                f"        _ct_plt.figure(_ct_n).savefig(os.path.join('{escaped_figs}', 'figure_%d.png' % _ct_n))",
                "except Exception as e:",
                "    result['warnings'].append('could not save figures: %s' % e)",
                "",
            ])

        lines.extend([
            "# Write result to file",
            f"with open('{escaped_result}', 'w') as f:",
            "    json.dump(result, f)",
        ])

        return "\n".join(lines)

    def _collect_artifacts(self, sandbox_dir: str) -> None:
        """Copy saved figures out of the job's private dir (#237).

        Only ``figure_<n>.png`` regular files directly in the figures dir are
        taken, read without following symlinks and capped in size.
        """
        if not (self.graphics and self.figure_dir):
            return
        figures = os.path.join(sandbox_dir, FIGURE_SUBDIR)
        if not os.path.isdir(figures) or os.path.islink(figures):
            return
        for name in sorted(os.listdir(figures))[:MAX_FIGURES]:
            if not _FIGURE_NAME.fullmatch(name):
                continue
            try:
                data = read_untrusted_bytes(os.path.join(figures, name),
                                            root=sandbox_dir)
            except OSError:
                continue
            target = os.path.join(self.figure_dir, f"{self.figure_prefix}_{name}")
            with open(target, "wb") as f:
                f.write(data)

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
        # Security pre-check if enabled
        if self.security_check and SANDBOX_AVAILABLE:
            full_path = script_path if os.path.isabs(script_path) else os.path.join(self.working_dir, script_path)
            try:
                # Student-controlled: no symlinks/FIFOs, size-capped (#237).
                code = read_untrusted_text(full_path)
                report = analyze_python_security(code)
                if not report.safe:
                    return {
                        "status": "BLOCKED",
                        "errors": [f"Security check failed: {issue.message}"
                                  for issue in report.issues[:5]],
                        "warnings": [],
                        "variables": {},
                        "stdout": "",
                        "stderr": "",
                        "traceback": {},
                        "exectime": 0,
                    }
            except Exception:
                pass  # Continue if security check fails

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
