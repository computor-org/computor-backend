"""
Fortran Testing Framework - Test Class

Main test execution logic for Fortran code testing.
"""

import glob as globlib
import os
import re
import pytest

from ctcore.security import safe_regex_search, RegexTimeoutError

from ctcore.models import (
    ComputorTestSuite,
    ComputorTestCollection,
    ComputorTest,
    ComputorSpecification,
    ComputorReport,
    TypeEnum,
    StatusEnum,
    ResultEnum,
    QualificationEnum,
)
from .conftest import report_key, Solution
from testers.executors.fortran import FortranExecutor, analyze_source, FORTRAN_DEFAULTS
from ctcore.helpers import get_property_as_list
from ctcore.stdio import (
    compare_outputs,
    match_exit_code,
)
from ..test_base import main_idx_by_dependency, check_file_exists


def get_source_files(main: ComputorTestCollection, directory: str) -> list:
    """Get Fortran source files for compilation."""
    if main.sourceFiles:
        return main.sourceFiles

    # Auto-detect Fortran source files
    extensions = (
        FORTRAN_DEFAULTS["extensions"]["fixed"] +
        FORTRAN_DEFAULTS["extensions"]["free"]
    )

    all_sources = []
    for ext in extensions:
        pattern = os.path.join(directory, f"*{ext}")
        all_sources.extend(globlib.glob(pattern))

    # Prefer entry point if specified
    if main.entryPoint:
        entry_path = os.path.join(directory, main.entryPoint)
        if os.path.exists(entry_path):
            return [main.entryPoint]

    # Return all source files found
    return [os.path.basename(f) for f in all_sources]


def get_solution(pytestconfig, idx: int, where: Solution) -> dict:
    """
    Get or compute solution for a test.

    Compiles and executes Fortran code if not already cached.
    """
    _report = pytestconfig.stash[report_key]
    testsuite: ComputorTestSuite = _report["testsuite"]
    specification: ComputorSpecification = _report["specification"]
    report: ComputorReport = _report["report"]
    solutions = _report["solutions"]
    root = _report["root"]

    idx_str = str(idx)
    main: ComputorTestCollection = testsuite.properties.tests[idx]

    if idx_str in solutions and where in solutions[idx_str]:
        return solutions[idx_str][where]

    if idx_str not in solutions:
        solutions[idx_str] = {}

    _solution = solutions[idx_str]
    _dir = (specification.studentDirectory if where == Solution.student
            else specification.referenceDirectory)

    timeout = main.timeout or 30.0
    input_answers = get_property_as_list(main.inputAnswers)
    success_dependencies = get_property_as_list(main.successDependency)

    error = False
    errormsg = ""
    status = StatusEnum.scheduled

    # Check success dependencies
    for dependency in success_dependencies:
        _idx = main_idx_by_dependency(testsuite, dependency)
        if _idx is None:
            error = True
            errormsg = f"Success-Dependency `{success_dependencies}` not valid"
            status = StatusEnum.failed
        else:
            total = report.tests[_idx].summary.total
            for sub_idx in range(total):
                result = report.tests[_idx].tests[sub_idx].result
                if result != ResultEnum.passed:
                    error = True
                    errormsg = f"Success-Dependency `{success_dependencies}` not satisfied"
                    status = StatusEnum.skipped
                    break
        if error:
            break

    if error:
        _solution[where] = {
            "status": status,
            "errormsg": errormsg,
            "compilation": None,
            "execution": None,
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }
        return _solution[where]

    # Get source files
    source_files = get_source_files(main, _dir)

    if not source_files:
        if where == Solution.student:
            _solution[where] = {
                "status": StatusEnum.failed,
                "errormsg": f"No Fortran source files found in {_dir}",
                "compilation": None,
                "execution": None,
                "stdout": "",
                "stderr": "",
                "exit_code": -1,
            }
        else:
            # Reference not found - create empty solution
            _solution[where] = {
                "status": StatusEnum.completed,
                "errormsg": "",
                "compilation": None,
                "execution": None,
                "stdout": "",
                "stderr": "",
                "exit_code": 0,
            }
        return _solution[where]

    # Compile and run
    try:
        with FortranExecutor(working_dir=_dir, timeout=timeout) as executor:
            # Compile
            compiler = main.compiler
            compiler_flags = main.compilerFlags
            linker_flags = main.linkerFlags

            comp_result = executor.compile(
                source_files=source_files,
                compiler=compiler,
                flags=compiler_flags,
                linker_flags=linker_flags,
                output_name=main.executableName
            )

            if not comp_result.success:
                _solution[where] = {
                    "status": StatusEnum.failed,
                    "errormsg": f"Compilation failed: {comp_result.stderr}",
                    "compilation": comp_result,
                    "execution": None,
                    "stdout": comp_result.stdout,
                    "stderr": comp_result.stderr,
                    "exit_code": comp_result.return_code,
                }
                return _solution[where]

            # Run
            stdin_input = "\n".join(input_answers) if input_answers else None
            args = main.args
            environment = main.environment

            exec_result = executor.run(
                args=args,
                stdin=stdin_input,
            )

            if exec_result.timed_out:
                _solution[where] = {
                    "status": StatusEnum.timedout,
                    "errormsg": f"Execution timed out after {timeout} seconds",
                    "compilation": comp_result,
                    "execution": exec_result,
                    "stdout": exec_result.stdout,
                    "stderr": exec_result.stderr,
                    "exit_code": exec_result.return_code,
                }
            else:
                _solution[where] = {
                    "status": StatusEnum.completed,
                    "errormsg": "",
                    "compilation": comp_result,
                    "execution": exec_result,
                    "stdout": exec_result.stdout,
                    "stderr": exec_result.stderr,
                    "exit_code": exec_result.return_code,
                }

    except Exception as e:
        _solution[where] = {
            "status": StatusEnum.crashed,
            "errormsg": f"Unexpected error: {e}",
            "compilation": None,
            "execution": None,
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }

    return _solution[where]


class TestComputorFortran:
    """Main test class for Fortran code testing."""

    def test_entrypoint(self, pytestconfig, testcases):
        """
        Execute a single test case.

        Args:
            pytestconfig: Pytest configuration
            testcases: Tuple of (main_idx, sub_idx)
        """
        idx_main, idx_sub = testcases

        _report = pytestconfig.stash[report_key]
        testsuite: ComputorTestSuite = _report["testsuite"]
        specification: ComputorSpecification = _report["specification"]
        main: ComputorTestCollection = testsuite.properties.tests[idx_main]
        sub: ComputorTest = main.tests[idx_sub]

        dir_reference = specification.referenceDirectory
        dir_student = specification.studentDirectory

        testtype = main.type
        file = main.file

        name = sub.name
        value = sub.value
        pattern = sub.pattern
        qualification = sub.qualification or QualificationEnum.verifyEqual

        # Get test options
        ignore_case = sub.ignoreCase or False
        ignore_whitespace = sub.ignoreWhitespace or False
        trim_output = sub.trimOutput if sub.trimOutput is not None else True
        normalize_newlines = sub.normalizeNewlines if sub.normalizeNewlines is not None else True
        numeric_tolerance = sub.numericTolerance or 1e-6
        line_number = sub.lineNumber

        # stdio tests (stdout, stderr, stdio)
        if testtype in [TypeEnum.stdout, TypeEnum.stderr, TypeEnum.stdio]:
            try:
                _solution_student = get_solution(pytestconfig, idx_main, Solution.student)
                _solution_reference = get_solution(pytestconfig, idx_main, Solution.reference)
            except Exception as e:
                pytest.fail(f"Getting solution failed: {e}")

            if _solution_student["status"] == StatusEnum.skipped:
                pytest.skip(_solution_student["errormsg"])
            elif _solution_student["status"] == StatusEnum.timedout:
                pytest.fail(f"Execution timed out: {_solution_student['errormsg']}")
            elif _solution_student["status"] != StatusEnum.completed:
                pytest.fail(_solution_student["errormsg"])

            # Get the appropriate output
            if testtype == TypeEnum.stderr:
                actual = _solution_student["stderr"]
                expected = sub.expectedStderr or _solution_reference.get("stderr", "")
            else:
                actual = _solution_student["stdout"]
                expected = sub.expectedStdout or _solution_reference.get("stdout", "")

            # Handle list expected values
            if isinstance(expected, list):
                expected = "\n".join(expected)

            # Use sub.value as expected if provided
            if value is not None:
                if isinstance(value, list):
                    expected = "\n".join(str(v) for v in value)
                else:
                    expected = str(value)

            # Compare based on qualification
            result = compare_outputs(
                actual=actual,
                expected=expected,
                qualification=str(qualification),
                pattern=pattern,
                ignore_case=ignore_case,
                trim=trim_output,
                normalize_newlines=normalize_newlines,
                line_number=line_number,
                tolerance=numeric_tolerance,
                exit_code=_solution_student["exit_code"]
            )

            if not result.success:
                msg = result.message
                if result.actual and result.expected:
                    msg += f"\n  Actual: {result.actual[:200]}"
                    msg += f"\n  Expected: {result.expected[:200]}"
                pytest.fail(msg)

        # Exit code tests
        elif testtype == TypeEnum.exitcode:
            try:
                _solution_student = get_solution(pytestconfig, idx_main, Solution.student)
            except Exception as e:
                pytest.fail(f"Getting solution failed: {e}")

            if _solution_student["status"] == StatusEnum.skipped:
                pytest.skip(_solution_student["errormsg"])
            elif _solution_student["status"] == StatusEnum.timedout:
                pytest.fail("Execution timed out")

            actual_code = _solution_student["exit_code"]
            expected_code = sub.expectedExitCode if sub.expectedExitCode is not None else 0

            if value is not None:
                expected_code = int(value)

            result = match_exit_code(actual_code, expected_code)
            if not result.success:
                pytest.fail(f"Exit code mismatch: got {actual_code}, expected {expected_code}")

        # Compile tests (check compilation success/failure)
        elif testtype == TypeEnum.compile:
            try:
                _solution_student = get_solution(pytestconfig, idx_main, Solution.student)
            except Exception as e:
                pytest.fail(f"Getting solution failed: {e}")

            comp = _solution_student.get("compilation")

            # Check if we expect success or failure
            expect_success = True
            if value is not None:
                expect_success = bool(value)

            if comp is None:
                pytest.fail("Compilation result not available")

            if expect_success:
                if not comp.success:
                    pytest.fail(f"Compilation should succeed but failed:\n{comp.stderr}")
            else:
                if comp.success:
                    pytest.fail("Compilation should fail but succeeded")

            # Check for specific error/warning patterns
            if pattern:
                combined = comp.stdout + comp.stderr
                try:
                    if not safe_regex_search(pattern, combined):
                        pytest.fail(f"Expected pattern not found in compiler output: {pattern}")
                except RegexTimeoutError:
                    pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")

        # Exist tests (check file exists)
        elif testtype == TypeEnum.exist:
            file_pattern = name if not file else os.path.join(file, name)
            student_path = os.path.join(dir_student, file_pattern)
            matches = globlib.glob(student_path)

            if not matches:
                pytest.fail(f"File '{file_pattern}' not found in student directory")

            # Check for empty files if allowEmpty is False (default)
            allow_empty = getattr(sub, 'allowEmpty', False)
            if not allow_empty:
                for filepath in matches:
                    if os.path.isfile(filepath) and os.path.getsize(filepath) == 0:
                        rel_path = os.path.relpath(filepath, dir_student)
                        pytest.fail(f"File '{rel_path}' is empty (0 bytes)")

            _report["student_file_list"].extend(matches)

        # Structural tests (check for Fortran constructs)
        elif testtype == TypeEnum.structural:
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
            if name == "program":
                if not analysis["has_program"]:
                    pytest.fail("program statement not found")

            elif name in analysis.get("programs", []):
                # Program exists
                pass

            elif name in analysis.get("modules", []):
                # Module exists
                pass

            elif name in analysis.get("subroutines", []):
                # Subroutine exists
                pass

            elif name in analysis.get("functions", []):
                # Function exists
                pass

            elif name in analysis.get("keywords", {}):
                count = analysis["keywords"][name]
                allowed_range = sub.allowedOccuranceRange
                if allowed_range:
                    c_min, c_max = allowed_range
                    if c_max == 0:
                        c_max = float('inf')
                    if not (c_min <= count <= c_max):
                        pytest.fail(f"`{name}` found {count} times, expected {c_min}-{c_max}")
                elif value is not None:
                    if count != int(value):
                        pytest.fail(f"`{name}` found {count} times, expected {value}")

            else:
                # Check if it's in the source
                with open(file_path, 'r') as f:
                    content = f.read()

                if pattern:
                    try:
                        if not safe_regex_search(pattern, content, re.IGNORECASE):
                            pytest.fail(f"Pattern `{pattern}` not found in source")
                    except RegexTimeoutError:
                        pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")
                else:
                    if name.lower() not in content.lower():
                        pytest.fail(f"`{name}` not found in source")

        # Error tests (expect compilation or runtime error)
        elif testtype == TypeEnum.error:
            try:
                _solution_student = get_solution(pytestconfig, idx_main, Solution.student)
            except Exception as e:
                pytest.fail(f"Getting solution failed: {e}")

            # Check for errors
            has_error = (
                _solution_student["status"] in [StatusEnum.failed, StatusEnum.crashed] or
                _solution_student["exit_code"] != 0
            )

            if not has_error:
                pytest.fail("Expected an error but execution succeeded")

            # Check error pattern if specified
            if pattern:
                error_output = _solution_student["stderr"] + _solution_student["errormsg"]
                try:
                    if not safe_regex_search(pattern, error_output):
                        pytest.fail(f"Expected error matching `{pattern}` not found")
                except RegexTimeoutError:
                    pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")

        # Warning tests
        elif testtype == TypeEnum.warning:
            try:
                _solution_student = get_solution(pytestconfig, idx_main, Solution.student)
            except Exception as e:
                pytest.fail(f"Getting solution failed: {e}")

            comp = _solution_student.get("compilation")
            if not comp:
                pytest.skip("No compilation result available")

            if not comp.warnings:
                pytest.fail("Expected warnings but none found")

            if pattern:
                try:
                    found = any(safe_regex_search(pattern, w) for w in comp.warnings)
                except RegexTimeoutError:
                    pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")
                if not found:
                    pytest.fail(f"Expected warning matching `{pattern}` not found")

        # Runtime tests (check execution time, etc.)
        elif testtype == TypeEnum.runtime:
            try:
                _solution_student = get_solution(pytestconfig, idx_main, Solution.student)
            except Exception as e:
                pytest.fail(f"Getting solution failed: {e}")

            exec_result = _solution_student.get("execution")
            if not exec_result:
                pytest.fail("No execution result available")

            # Check execution time limit
            if value is not None:
                max_time = float(value)
                if exec_result.duration > max_time:
                    pytest.fail(f"Execution took {exec_result.duration:.3f}s, "
                               f"limit is {max_time}s")

        else:
            pytest.skip(f"Unknown test type: {testtype}")
