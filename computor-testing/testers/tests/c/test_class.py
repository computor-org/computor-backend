"""
C/C++ Testing Framework - Test Class

Main test execution logic for C/C++ code testing.
Uses the base classes for common functionality.
"""

import glob as globlib
import os
import re

import pytest

from ctcore.security import safe_regex_search, RegexTimeoutError

from ctcore.models import (
    ComputorTestCollection,
    TypeEnum,
    StatusEnum,
)
from ctcore.helpers import get_property_as_list
from testers.executors.c import CExecutor, analyze_source

from .conftest import report_key
from ..test_base import (
    Solution,
    CompiledSolutionManager,
    CompiledTestClass,
)


def get_source_files(main: ComputorTestCollection, directory: str) -> list:
    """Get source files for compilation."""
    if main.sourceFiles:
        return main.sourceFiles

    # Auto-detect source files
    c_files = globlib.glob(os.path.join(directory, "*.c"))
    cpp_files = globlib.glob(os.path.join(directory, "*.cpp"))
    cpp_files += globlib.glob(os.path.join(directory, "*.cxx"))
    cpp_files += globlib.glob(os.path.join(directory, "*.cc"))

    # Prefer entry point if specified
    if main.entryPoint:
        entry_path = os.path.join(directory, main.entryPoint)
        if os.path.exists(entry_path):
            return [main.entryPoint]

    # Return all source files found
    all_sources = c_files + cpp_files
    return [os.path.basename(f) for f in all_sources]


class CSolutionManager(CompiledSolutionManager):
    """Solution manager for C/C++ code execution."""

    def _execute_solution(self, idx: int, where: Solution) -> dict:
        """Compile and execute C/C++ code."""
        main: ComputorTestCollection = self.testsuite.properties.tests[idx]
        _dir = self.get_directory(where)

        timeout = main.timeout or 30.0
        input_answers = get_property_as_list(main.inputAnswers)

        # Get source files
        source_files = get_source_files(main, _dir)

        if not source_files:
            if where == Solution.student:
                return {
                    "status": StatusEnum.failed,
                    "errormsg": f"No source files found in {_dir}",
                    "compilation": None,
                    "execution": None,
                    "stdout": "",
                    "stderr": "",
                    "exit_code": -1,
                }
            else:
                # Reference not found - create empty solution
                return {
                    "status": StatusEnum.completed,
                    "errormsg": "",
                    "compilation": None,
                    "execution": None,
                    "stdout": "",
                    "stderr": "",
                    "exit_code": 0,
                }

        # Compile and run
        try:
            with CExecutor(working_dir=_dir, timeout=timeout) as executor:
                # Compile
                comp_result = executor.compile(
                    source_files=source_files,
                    compiler=main.compiler,
                    flags=main.compilerFlags,
                    linker_flags=main.linkerFlags,
                    output_name=main.executableName
                )

                if not comp_result.success:
                    return {
                        "status": StatusEnum.failed,
                        "errormsg": f"Compilation failed: {comp_result.stderr}",
                        "compilation": comp_result,
                        "execution": None,
                        "stdout": comp_result.stdout,
                        "stderr": comp_result.stderr,
                        "exit_code": comp_result.return_code,
                    }

                # Run
                stdin_input = "\n".join(input_answers) if input_answers else None
                exec_result = executor.run(
                    args=main.args,
                    stdin=stdin_input,
                )

                if exec_result.timed_out:
                    return {
                        "status": StatusEnum.timedout,
                        "errormsg": f"Execution timed out after {timeout} seconds",
                        "compilation": comp_result,
                        "execution": exec_result,
                        "stdout": exec_result.stdout,
                        "stderr": exec_result.stderr,
                        "exit_code": exec_result.return_code,
                    }

                return self._create_completed_solution(
                    comp_result, exec_result,
                    exec_result.stdout, exec_result.stderr,
                    exec_result.return_code
                )

        except Exception as e:
            return {
                "status": StatusEnum.crashed,
                "errormsg": f"Unexpected error: {e}",
                "compilation": None,
                "execution": None,
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
            }


# Singleton solution manager per pytestconfig
_solution_managers = {}


def get_solution_manager(pytestconfig) -> CSolutionManager:
    """Get or create the solution manager for this test run."""
    config_id = id(pytestconfig)
    if config_id not in _solution_managers:
        _solution_managers[config_id] = CSolutionManager(pytestconfig, report_key)
    return _solution_managers[config_id]


class TestComputorC(CompiledTestClass):
    """Main test class for C/C++ code testing."""

    def get_report_key(self):
        """Get the report key for accessing pytestconfig.stash."""
        return report_key

    def get_solution_manager(self, pytestconfig) -> CSolutionManager:
        """Get the solution manager for this test class."""
        return get_solution_manager(pytestconfig)

    def _test_language_specific(self, context):
        """Handle C/C++ specific test types."""
        testtype = context["testtype"]

        if testtype in [TypeEnum.stdout, TypeEnum.stderr, TypeEnum.stdio]:
            self._test_stdio(context)
        elif testtype == TypeEnum.exitcode:
            self._test_exitcode(context)
        elif testtype == TypeEnum.compile:
            self._test_compile(context)
        elif testtype == TypeEnum.runtime:
            self._test_runtime(context)
        else:
            pytest.skip(f"Unknown test type: {testtype}")

    def _test_structural(self, context):
        """Handle structural test type for C/C++."""
        main = context["main"]
        sub = context["sub"]
        file = context["file"]
        name = context["name"]
        value = context["value"]
        pattern = context["pattern"]
        dir_student = context["dir_student"]

        if file:
            file_path = os.path.join(dir_student, file)
        else:
            # Find main source file
            sources = get_source_files(main, dir_student)
            file_path = os.path.join(dir_student, sources[0]) if sources else None

        if not file_path or not os.path.exists(file_path):
            pytest.fail("Source file not found for structural test")

        analysis = analyze_source(file_path)

        if "error" in analysis:
            pytest.fail(f"Analysis failed: {analysis['error']}")

        # Check based on name
        if name == "main":
            if not analysis["main_function"]:
                pytest.fail("main() function not found")

        elif name in analysis.get("keywords", {}):
            count = analysis["keywords"][name]
            allowed_range = context["allowed_occurance_range"]
            if allowed_range:
                c_min, c_max = allowed_range
                if c_max == 0:
                    c_max = float('inf')
                if not (c_min <= count <= c_max):
                    pytest.fail(f"`{name}` found {count} times, expected {c_min}-{c_max}")
            elif value is not None:
                if count != int(value):
                    pytest.fail(f"`{name}` found {count} times, expected {value}")

        elif name in analysis.get("functions", []):
            # Function exists
            pass

        else:
            # Check if it's in the source
            with open(file_path, 'r') as f:
                content = f.read()

            if pattern:
                try:
                    if not safe_regex_search(pattern, content):
                        pytest.fail(f"Pattern `{pattern}` not found in source")
                except RegexTimeoutError:
                    pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")
            else:
                if name not in content:
                    pytest.fail(f"`{name}` not found in source")
