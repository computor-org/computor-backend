"""
Octave code execution module.

This module handles the execution of Octave code files and scripts,
extracting variables from the Octave workspace for comparison.

SECURITY: This module uses safe environment handling to prevent
leaking secrets to Octave processes.
"""

import os
import re
import json
import time
import tempfile
import subprocess
import logging
from typing import Dict, Any, Optional, List, Tuple

import numpy as np

from ctexec import InterpretedExecutor, ExecutorResult, ResourceLimits, make_preexec_fn
from ctexec.exceptions import ExecutionError

logger = logging.getLogger(__name__)

# Octave executable - can be overridden via environment variable
OCTAVE_EXECUTABLE = os.environ.get("OCTAVE_EXECUTABLE", "octave-cli")


class OctaveExecutionError(ExecutionError):
    """Exception raised when Octave execution fails."""
    pass


class OctaveExecutor(InterpretedExecutor):
    """
    Executes Octave code and retrieves workspace variables.

    This class provides methods to run Octave scripts and extract
    variables from the workspace for testing purposes.
    """

    language = "octave"

    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
        check_runtime: bool = True,
    ):
        """
        Initialize the Octave executor.

        Args:
            working_dir: Directory to execute Octave code in
            timeout: Maximum execution time in seconds
            check_runtime: Check if Octave runtime is available
        """
        super().__init__(working_dir, timeout, use_safe_env=True, check_runtime=check_runtime)
        # Legacy state attributes
        self.namespace: Dict[str, Any] = {}
        self.error: str = ""
        self.stdout: str = ""
        self.stderr: str = ""
        self.execution_time: float = 0.0
        self.figure_handles: List[int] = []

    def _get_interpreter_command(self) -> List[str]:
        """Get the Octave interpreter command."""
        return [OCTAVE_EXECUTABLE, "--no-gui", "--no-window-system", "--silent"]

    def _get_wrapper_extension(self) -> str:
        """Get file extension for wrapper scripts."""
        return ".m"

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
        Build a wrapper script that executes the Octave code and extracts variables.
        """
        escaped_result = self.escape_path(result_path)

        # Get script base name (strip .m extension)
        base_name = os.path.splitext(os.path.basename(script_path))[0]

        lines = [
            "% Auto-generated wrapper for safe execution",
            "",
            "% Set random seed for reproducibility",
            "rand('seed', 1);",
            "randn('seed', 1);",
            "",
            "% Close all figures",
            "close all;",
            "",
        ]

        # Run the main file
        if script_path:
            lines.extend([
                f"% Execute main script",
                f"run('{base_name}');",
                "",
            ])

        # Run setup code
        if setup_code:
            lines.append("% Setup code")
            for code in setup_code:
                if code:
                    lines.append(code)
            lines.append("")

        # Run teardown code
        if teardown_code:
            lines.append("% Teardown code")
            for code in teardown_code:
                if code:
                    lines.append(code)
            lines.append("")

        # Add variable extraction code
        lines.append(self._generate_extraction_code(variables_to_extract, escaped_result))

        return "\n".join(lines)

    def _generate_extraction_code(self, variables: List[str], result_path: str) -> str:
        """
        Generate Octave code to extract variables to JSON.

        Args:
            variables: List of variable names to extract
            result_path: Path to save the JSON results

        Returns:
            Octave code string for variable extraction
        """
        code = f"""
% Variable extraction for testing
__octester_vars_data__ = struct();
__octester_vars__ = {{{', '.join(f"'{v}'" for v in variables)}}};
for __i__ = 1:length(__octester_vars__)
    __varname__ = __octester_vars__{{__i__}};
    try
        __val__ = eval(__varname__);
        if isnumeric(__val__) && ~isscalar(__val__)
            __octester_vars_data__.(__varname__) = struct('__type__', 'array', '__shape__', size(__val__), '__data__', __val__(:)');
        else
            __octester_vars_data__.(__varname__) = __val__;
        end
    catch
        __octester_vars_data__.(__varname__) = struct('__error__', ['Variable not found: ' __varname__]);
    end
end

% Build result with status
__octester_result__ = struct();
__octester_result__.status = 'COMPLETED';
__octester_result__.variables = __octester_vars_data__;

% Save to JSON
__fid__ = fopen('{result_path}', 'w');
fprintf(__fid__, '%s', jsonencode(__octester_result__));
fclose(__fid__);
"""
        return code

    def execute_file(
        self,
        filename: str,
        setup_code: Optional[List[str]] = None,
        teardown_code: Optional[List[str]] = None,
        input_answers: Optional[List[str]] = None,
        variables_to_extract: Optional[List[str]] = None,
    ) -> bool:
        """
        Execute an Octave file and extract variables.

        This is the legacy interface for backwards compatibility.
        New code should use execute() instead.

        Args:
            filename: The Octave file to execute (relative to working_dir)
            setup_code: List of setup code lines to run after the file
            teardown_code: List of teardown code lines to run after setup
            input_answers: List of input answers for interactive scripts
            variables_to_extract: List of variable names to extract

        Returns:
            True if execution succeeded, False otherwise
        """
        setup_code = setup_code or []
        teardown_code = teardown_code or []
        input_answers = input_answers or []
        variables_to_extract = variables_to_extract or []

        # Convert input_answers to input_data string
        input_data = "\n".join(input_answers) if input_answers else None

        # Resolve filename to full path
        if filename:
            script_path = os.path.join(self.working_dir, filename)
        else:
            script_path = None

        # Use parent class execute()
        result = self.execute(
            source_path=script_path,
            variables_to_extract=variables_to_extract,
            setup_code=setup_code,
            teardown_code=teardown_code,
            input_data=input_data,
        )

        # Update legacy state
        self.stdout = result.stdout
        self.stderr = result.stderr
        self.execution_time = result.duration
        self.error = result.error_message if not result.success else ""

        # Deserialize and store variables
        if result.namespace:
            self.namespace = self._deserialize_variables(result.namespace)

        return result.success

    def execute_code(
        self,
        code: str,
        variables_to_extract: Optional[List[str]] = None,
    ) -> bool:
        """
        Execute arbitrary Octave code.

        Args:
            code: Octave code to execute
            variables_to_extract: List of variable names to extract

        Returns:
            True if execution succeeded, False otherwise
        """
        variables_to_extract = variables_to_extract or []

        # Create result file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as result_file:
            result_path = result_file.name

        # Build script
        script_lines = [
            "rand('seed', 1);",
            "randn('seed', 1);",
            code,
            self._generate_extraction_code(variables_to_extract, result_path),
        ]

        # Write script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.m', delete=False) as script_file:
            script_file.write('\n'.join(script_lines))
            script_path = script_file.name

        try:
            start_time = time.time()
            success = self._run_octave(script_path)
            self.execution_time = time.time() - start_time

            if success and os.path.exists(result_path):
                self._load_results(result_path)

            return success

        finally:
            for path in [script_path, result_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except OSError:
                        pass

    def _run_octave(self, script_path: str, input_path: str = None) -> bool:
        """
        Run Octave with the given script.

        Args:
            script_path: Path to the Octave script
            input_path: Optional path to input file for stdin

        Returns:
            True if execution succeeded, False otherwise
        """
        cmd = self._get_interpreter_command() + [script_path]

        # Set up preexec for resource limits (Unix only)
        limits = ResourceLimits(
            timeout=self.timeout,
            cpu_seconds=int(self.timeout),
            memory_bytes=512 * 1024 * 1024,  # 512 MB for Octave
            max_processes=10,
        )
        preexec = make_preexec_fn(limits)

        env = self._get_env()

        stdin_file = None
        try:
            if input_path:
                stdin_file = open(input_path, 'r')

            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                stdin=stdin_file,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
                preexec_fn=preexec,
            )

            self.stdout = result.stdout
            self.stderr = result.stderr

            if result.returncode != 0:
                self.error = f"Octave returned non-zero exit code: {result.returncode}\n{self.stderr}"
                return False

            # Check for errors in stderr (Octave may still exit 0 with errors)
            if "error:" in self.stderr.lower():
                self.error = self.stderr
                return False

            return True

        except subprocess.TimeoutExpired:
            self.error = f"Execution timed out after {self.timeout} seconds"
            return False

        except FileNotFoundError:
            self.error = f"Octave executable not found: {OCTAVE_EXECUTABLE}"
            return False

        except Exception as e:
            self.error = f"Execution failed: {str(e)}"
            return False

        finally:
            if stdin_file:
                stdin_file.close()

    def _load_results(self, result_path: str) -> None:
        """
        Load extracted variables from JSON file.

        Args:
            result_path: Path to the JSON results file
        """
        try:
            with open(result_path, 'r') as f:
                data = json.load(f)

            for name, value in data.items():
                self.namespace[name] = self._deserialize_value(value)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Octave results: {e}")
        except Exception as e:
            logger.warning(f"Failed to load Octave results: {e}")

    def _deserialize_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize variables from JSON format."""
        result = {}
        for name, value in variables.items():
            result[name] = self._deserialize_value(value)
        return result

    def _deserialize_value(self, value: Any) -> Any:
        """
        Deserialize a value from JSON format.

        Args:
            value: The JSON value to deserialize

        Returns:
            Python/NumPy representation of the value
        """
        if isinstance(value, dict):
            if '__error__' in value:
                return None
            if '__type__' in value:
                vtype = value['__type__']
                if vtype == 'array':
                    shape = tuple(value['__shape__'])
                    data = np.array(value['__data__'])
                    return data.reshape(shape) if len(shape) > 1 else data
                elif vtype == 'cell':
                    shape = tuple(value['__shape__'])
                    data = [self._deserialize_value(v) for v in value['__data__']]
                    # Return as nested list for cell arrays
                    if len(shape) == 2 and shape[0] == 1:
                        return data
                    return data
                elif vtype == 'struct':
                    return value['__data__']
                else:
                    return value.get('__repr__', str(value))
            return value
        return value


def check_octave_installed() -> Tuple[bool, str]:
    """
    Check if Octave is installed and get version info.

    Returns:
        Tuple of (is_installed, version_info)
    """
    return OctaveExecutor.check_installed()


def run_structural_analysis(file_path: str, keywords: List[str]) -> Dict[str, int]:
    """
    Analyze Octave file for structural elements (keywords).

    Args:
        file_path: Path to the Octave file
        keywords: List of keywords to count

    Returns:
        Dictionary mapping keywords to their occurrence counts
    """
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return {kw: 0 for kw in keywords}

    # Remove comments and strings to avoid false positives
    content = _strip_comments_and_strings(content)

    counts = {}
    for keyword in keywords:
        # Match keyword as whole word
        pattern = rf'\b{re.escape(keyword)}\b'
        matches = re.findall(pattern, content)
        counts[keyword] = len(matches)

    return counts


def _strip_comments_and_strings(content: str) -> str:
    """
    Remove comments and string literals from Octave code.

    Args:
        content: Octave source code

    Returns:
        Code with comments and strings removed
    """
    # Remove line comments (% and #)
    content = re.sub(r'[%#].*$', '', content, flags=re.MULTILINE)

    # Remove block comments (%{ ... %})
    content = re.sub(r'%\{.*?%\}', '', content, flags=re.DOTALL)

    # Remove single-quoted strings
    content = re.sub(r"'[^']*'", '""', content)

    # Remove double-quoted strings
    content = re.sub(r'"[^"]*"', '""', content)

    return content


def check_file_exists(directory: str, pattern: str) -> Tuple[bool, List[str]]:
    """
    Check if files matching a pattern exist in a directory.

    Args:
        directory: Directory to search in
        pattern: File pattern (can include wildcards)

    Returns:
        Tuple of (exists, list of matching files)
    """
    import glob

    search_path = os.path.join(directory, pattern)
    matches = glob.glob(search_path)

    # Get relative paths
    rel_matches = [os.path.relpath(m, directory) for m in matches]

    return len(matches) > 0, rel_matches


def extract_graphics_data(
    executor: OctaveExecutor,
    graphics_specs: List[str],
    artifact_dir: str = None,
    source: str = "student",
    test_index: int = 0,
) -> Dict[str, Any]:
    """
    Extract graphics data from Octave figures.

    Args:
        executor: OctaveExecutor with executed code
        graphics_specs: List of graphics property specifications
        artifact_dir: Directory to save figure artifacts
        source: 'student' or 'reference'
        test_index: Index of the current test

    Returns:
        Dictionary of extracted graphics properties
    """
    results = {}

    # Build extraction code for graphics
    extraction_code = []
    for spec in graphics_specs:
        # Parse specification like "figure(1).axes(1).XLim"
        var_name = spec.replace('.', '_').replace('(', '_').replace(')', '')
        extraction_code.append(f"try; {var_name} = {spec}; catch; end;")

    # Save figures if artifact directory specified
    if artifact_dir:
        extraction_code.append(f"""
__figs__ = get(0, 'children');
for __i__ = 1:length(__figs__)
    __fname__ = sprintf('{artifact_dir}/{source}_test_{test_index}_figure_%d.png', __i__);
    saveas(__figs__(__i__), __fname__);
end
""")

    # This is a simplified approach - full implementation would
    # need to re-execute with graphics extraction

    return results
