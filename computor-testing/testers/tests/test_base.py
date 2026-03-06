"""
Base Classes for Testing Framework

Provides common functionality for all language-specific test classes.
"""

import glob as globlib
import os
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pytest
import numpy as np

from ctcore.security import safe_regex_findall, safe_regex_search, RegexTimeoutError

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
from ctcore.helpers import get_property_as_list, token_exchange


# =============================================================================
# Utility Functions
# =============================================================================

def main_idx_by_dependency(testsuite: ComputorTestSuite, dependency) -> Optional[int]:
    """
    Find the main test index by dependency (name, id, or index).

    Args:
        testsuite: The test suite containing tests
        dependency: The dependency identifier (name, id, or index)

    Returns:
        The index of the main test, or None if not found
    """
    if dependency is None or dependency == "":
        return None

    for idx, main in enumerate(testsuite.properties.tests):
        if main.name == dependency or main.id == dependency:
            return idx
        if isinstance(dependency, int) and idx == dependency:
            return idx
        if str(idx) == str(dependency):
            return idx

    return None


def check_file_exists(directory: str, pattern: str) -> Tuple[bool, List[str]]:
    """
    Check if files matching a pattern exist in a directory.

    Args:
        directory: The directory to search in
        pattern: The file pattern (can include wildcards)

    Returns:
        Tuple of (exists, list of matching files)
    """
    full_pattern = os.path.join(directory, pattern)
    matches = globlib.glob(full_pattern)

    if matches:
        return True, [os.path.relpath(m, directory) for m in matches]
    return False, []


def compare_values(actual, expected, rel_tol=None, abs_tol=None, name="value"):
    """
    Compare two values with tolerance. Raises AssertionError on mismatch.

    Args:
        actual: The actual value
        expected: The expected value
        rel_tol: Relative tolerance (default: 1e-9)
        abs_tol: Absolute tolerance (default: 1e-12)
        name: Variable name for error messages
    """
    rel_tol = rel_tol if rel_tol is not None else 1e-9
    abs_tol = abs_tol if abs_tol is not None else 1e-12

    if expected is None:
        assert actual is None, f"Expected None for '{name}', got {type(actual)}"
        return

    if actual is None:
        raise AssertionError(f"Variable '{name}' is None, expected {type(expected)}")

    # Handle numpy arrays
    if isinstance(expected, np.ndarray) or isinstance(actual, np.ndarray):
        actual = np.asarray(actual)
        expected = np.asarray(expected)

        if actual.shape != expected.shape:
            raise AssertionError(
                f"Shape mismatch for '{name}': {actual.shape} vs {expected.shape}"
            )

        if np.issubdtype(expected.dtype, np.number):
            if not np.allclose(actual, expected, rtol=rel_tol, atol=abs_tol):
                raise AssertionError(f"Array values differ for '{name}'")
        else:
            if not np.array_equal(actual, expected):
                raise AssertionError(f"Array values differ for '{name}'")
        return

    # Handle numeric scalars
    if isinstance(expected, (int, float)):
        if not isinstance(actual, (int, float)):
            raise AssertionError(
                f"Type mismatch for '{name}': {type(actual)} vs {type(expected)}"
            )

        if abs(expected) > 0:
            rel_diff = abs(actual - expected) / abs(expected)
            if rel_diff <= rel_tol:
                return

        abs_diff = abs(actual - expected)
        if abs_diff <= abs_tol:
            return

        raise AssertionError(f"Value mismatch for '{name}': {actual} vs {expected}")

    # Handle complex numbers
    if isinstance(expected, complex):
        if not isinstance(actual, complex):
            raise AssertionError(
                f"Type mismatch for '{name}': {type(actual)} vs {type(expected)}"
            )
        if not (abs(actual.real - expected.real) <= abs_tol and
                abs(actual.imag - expected.imag) <= abs_tol):
            raise AssertionError(f"Value mismatch for '{name}': {actual} vs {expected}")
        return

    # Handle strings
    if isinstance(expected, str):
        assert actual == expected, \
            f"String mismatch for '{name}': '{actual}' vs '{expected}'"
        return

    # Handle lists/tuples
    if isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)):
            raise AssertionError(f"Type mismatch for '{name}': expected list/tuple")

        if len(actual) != len(expected):
            raise AssertionError(
                f"Length mismatch for '{name}': {len(actual)} vs {len(expected)}"
            )

        for i, (a, e) in enumerate(zip(actual, expected)):
            compare_values(a, e, rel_tol, abs_tol, f"{name}[{i}]")
        return

    # Handle dicts
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise AssertionError(f"Type mismatch for '{name}': expected dict")

        if set(actual.keys()) != set(expected.keys()):
            raise AssertionError(
                f"Key mismatch for '{name}': {set(actual.keys())} vs {set(expected.keys())}"
            )

        for key in expected:
            compare_values(actual[key], expected[key], rel_tol, abs_tol, f"{name}[{key!r}]")
        return

    # Default comparison
    assert actual == expected, f"Value mismatch for '{name}': {actual} vs {expected}"


# =============================================================================
# Shared Test Helpers
# =============================================================================
# These functions extract duplicated logic from language-specific test_class.py
# files. Each language test_class.py can call these instead of reimplementing.


def check_success_dependencies(
    testsuite: ComputorTestSuite,
    report: ComputorReport,
    main: ComputorTestCollection,
    main_idx_fn=None,
) -> Tuple[bool, str, StatusEnum]:
    """
    Check success dependencies for a test collection.

    Args:
        testsuite: The test suite
        report: The report object
        main: The main test collection
        main_idx_fn: Optional custom dependency resolver (default: main_idx_by_dependency)

    Returns:
        Tuple of (has_error, error_message, status)
    """
    resolve = main_idx_fn or main_idx_by_dependency
    success_dependencies = get_property_as_list(main.successDependency)

    for dependency in success_dependencies:
        _idx = resolve(testsuite, dependency)
        if _idx is None:
            return True, f"Success-Dependency `{success_dependencies}` not valid", StatusEnum.failed

        total = report.tests[_idx].summary.total
        for sub_idx in range(total):
            result = report.tests[_idx].tests[sub_idx].result
            if result != ResultEnum.passed:
                return True, f"Success-Dependency `{success_dependencies}` not satisfied", StatusEnum.skipped

    return False, "", StatusEnum.scheduled


def check_setup_code_dependency(
    testsuite: ComputorTestSuite,
    solutions: dict,
    main: ComputorTestCollection,
    where: str,
    setup_code: List[str],
    main_idx_fn=None,
) -> Tuple[bool, str, StatusEnum, List[str]]:
    """
    Check setup code dependency and merge inherited setup code.

    Returns:
        Tuple of (has_error, error_message, status, updated_setup_code)
    """
    resolve = main_idx_fn or main_idx_by_dependency
    setup_code_dependency = main.setUpCodeDependency

    if not setup_code_dependency:
        return False, "", StatusEnum.scheduled, setup_code

    _idx = resolve(testsuite, setup_code_dependency)
    if _idx is None:
        return True, f"SetupCode-Dependency `{setup_code_dependency}` not valid", StatusEnum.failed, setup_code

    dep_idx = str(_idx)
    if dep_idx in solutions and where in solutions[dep_idx]:
        dep_setup = solutions[dep_idx][where].get("setup_code", [])
        setup_code = dep_setup + setup_code

    return False, "", StatusEnum.scheduled, setup_code


def apply_token_exchange_to_code(
    code_list: List[str], report: dict, where: str
) -> List[str]:
    """Apply token exchange to setup/teardown code lists."""
    file_list = report.get(f"{where}_file_list", [])
    command_list = report.get(f"{where}_command_list", [])
    return [token_exchange(code, file_list, command_list) for code in code_list]


def check_solution_status(solution: dict):
    """
    Check solution status and pytest.skip/fail as appropriate.

    Call after get_solution() before accessing variables.
    """
    if solution["status"] == StatusEnum.skipped:
        pytest.skip(solution["errormsg"])
    elif solution["status"] == StatusEnum.timedout:
        pytest.fail(f"Execution timed out: {solution['errormsg']}")
    elif solution["status"] != StatusEnum.completed:
        pytest.fail(solution["errormsg"])


def check_exist(
    name: str, file: Optional[str], dir_student: str,
    sub, report: dict,
):
    """
    Shared implementation for exist test type.

    Args:
        name: File name/pattern from sub.name
        file: Directory prefix from main.file
        dir_student: Student directory path
        sub: The sub-test object
        report: The _report dict (for storing file lists)
    """
    # When file is set, it IS the file to check; name is just the test identifier
    file_pattern = file if file else name
    student_path = os.path.join(dir_student, file_pattern)
    matches = globlib.glob(student_path)

    if not matches:
        pytest.fail(f"File '{file_pattern}' not found in student directory")

    allow_empty = getattr(sub, 'allowEmpty', False)
    if not allow_empty:
        for filepath in matches:
            if os.path.isfile(filepath) and os.path.getsize(filepath) == 0:
                rel_path = os.path.relpath(filepath, dir_student)
                pytest.fail(f"File '{rel_path}' is empty (0 bytes)")

    report.setdefault("student_file_list", []).extend(matches)
    return matches


def check_structural(
    name: str, pattern: Optional[str], file: Optional[str],
    dir_student: str, file_extensions: List[str],
    allowed_occurance_range: Optional[List[int]] = None,
    count_requirement=None,
):
    """
    Shared implementation for structural test type (simple text/regex counting).

    Args:
        name: Keyword/token to search for
        pattern: Optional regex pattern (overrides name)
        file: Specific file to check
        dir_student: Student directory path
        file_extensions: List of glob patterns to find source files (e.g. ["*.py"])
        allowed_occurance_range: [min, max] occurrence range
        count_requirement: Exact count requirement
    """
    if file:
        file_path = os.path.join(dir_student, file)
    else:
        file_path = None
        for ext in file_extensions:
            found = globlib.glob(os.path.join(dir_student, ext))
            if found:
                file_path = found[0]
                break

    if not file_path or not os.path.exists(file_path):
        pytest.fail(f"Source file not found for structural test")

    with open(file_path, 'r') as f:
        code = f.read()

    if pattern:
        try:
            occurrences = len(safe_regex_findall(pattern, code))
        except RegexTimeoutError:
            pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")
    else:
        occurrences = code.count(name)

    if allowed_occurance_range:
        min_occ, max_occ = allowed_occurance_range
        if max_occ == 0:
            max_occ = float('inf')
        assert min_occ <= occurrences <= max_occ, \
            f"'{name}' found {occurrences} times, expected {min_occ}-{max_occ}"
    elif count_requirement is not None:
        assert occurrences == count_requirement, \
            f"'{name}' found {occurrences} times, expected {count_requirement}"


def check_error(solution: dict, pattern: Optional[str] = None):
    """Shared implementation for error test type."""
    errors = solution.get("errors", [])

    if pattern:
        try:
            found = any(safe_regex_search(pattern, str(e)) for e in errors)
        except RegexTimeoutError:
            pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")
        assert found, f"Expected error matching `{pattern}` not found"
    else:
        assert len(errors) > 0, "Expected an error but none occurred"


def check_warning(solution: dict, pattern: Optional[str] = None):
    """Shared implementation for warning test type."""
    warnings = solution.get("warnings", [])

    if pattern:
        try:
            found = any(safe_regex_search(pattern, str(w)) for w in warnings)
        except RegexTimeoutError:
            pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")
        assert found, f"Expected warning matching `{pattern}` not found"
    else:
        assert len(warnings) > 0, "Expected a warning but none occurred"


def check_stdout(
    solution: dict, qualification, pattern: Optional[str] = None,
    value=None, ref_solution: dict = None,
):
    """
    Shared implementation for stdout test type (interpreted languages).

    Args:
        solution: Student solution dict
        qualification: QualificationEnum value
        pattern: Pattern string for matches/contains/regexp
        value: Expected value override
        ref_solution: Reference solution dict (for verifyEqual)
    """
    stdout = solution.get("stdout", "")
    # Some languages store stdout in a nested "std" dict
    if not stdout and "std" in solution:
        stdout = solution["std"].get("stdout", "") or ""

    if qualification == QualificationEnum.verifyEqual:
        expected = ""
        if value is not None:
            expected = str(value)
        elif ref_solution:
            expected = ref_solution.get("stdout", "")
            if not expected and "std" in ref_solution:
                expected = ref_solution["std"].get("stdout", "") or ""
        if stdout.strip() != expected.strip():
            pytest.fail(
                f"Output mismatch:\n  Actual: {stdout[:200]}\n  Expected: {expected[:200]}"
            )
    elif qualification == QualificationEnum.contains:
        assert pattern in stdout, f"Output does not contain '{pattern}'"
    elif qualification in (QualificationEnum.matches, QualificationEnum.regexp):
        try:
            match = safe_regex_search(pattern, stdout)
        except RegexTimeoutError:
            pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")
        assert match, f"Output does not match pattern '{pattern}'"


def compare_variable_by_qualification(
    val_student, name: str, qualification,
    pattern: Optional[str] = None,
    value=None,
    val_reference=None,
    relative_tolerance=None,
    absolute_tolerance=None,
    type_check: bool = False,
    shape_check: bool = False,
    ignore_class: bool = False,
    count_requirement=None,
):
    """
    Shared implementation for variable comparison by qualification type.

    Handles verifyEqual, matches, contains, startsWith, endsWith, regexp, count.
    """
    if qualification == QualificationEnum.verifyEqual:
        # Determine reference value
        if value is not None:
            ref = value
        elif val_reference is not None:
            ref = val_reference
        else:
            pytest.skip(f"Variable `{name}` not found in reference namespace")
            return

        # Type check
        if type_check and not ignore_class:
            type_student = type(val_student)
            type_reference = type(ref)
            if type_student != type_reference:
                if not _types_compatible(type_student, type_reference):
                    pytest.fail(
                        f"Variable `{name}` has incorrect type: "
                        f"{type_student} vs {type_reference}"
                    )

        # Shape check
        if shape_check:
            _check_shape_common(val_student, ref, name)

        # Value comparison
        compare_values(val_student, ref, relative_tolerance, absolute_tolerance, name)

    elif qualification == QualificationEnum.matches:
        assert str(val_student) == pattern, \
            f"Variable `{name}` does not match pattern `{pattern}`"

    elif qualification == QualificationEnum.contains:
        assert pattern in str(val_student), \
            f"Variable `{name}` does not contain `{pattern}`"

    elif qualification == QualificationEnum.startsWith:
        assert str(val_student).startswith(pattern), \
            f"Variable `{name}` does not start with `{pattern}`"

    elif qualification == QualificationEnum.endsWith:
        assert str(val_student).endswith(pattern), \
            f"Variable `{name}` does not end with `{pattern}`"

    elif qualification == QualificationEnum.regexp:
        try:
            match = safe_regex_search(pattern, str(val_student))
        except RegexTimeoutError:
            pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")
        assert match, f"Variable `{name}` does not match regex `{pattern}`"

    elif qualification == QualificationEnum.count:
        assert str(val_student).count(pattern) == count_requirement, \
            f"Variable `{name}` does not contain pattern `{pattern}` {count_requirement} times"

    else:
        pytest.skip(f"Unsupported qualification: {qualification}")


def _types_compatible(type1: type, type2: type) -> bool:
    """Check if two types are compatible for comparison."""
    numeric_types = (int, float, complex, np.integer, np.floating, np.complexfloating)
    if isinstance(type1, type) and isinstance(type2, type):
        try:
            if issubclass(type1, numeric_types) and issubclass(type2, numeric_types):
                return True
        except TypeError:
            pass
    if type1 == np.ndarray or type2 == np.ndarray:
        return True
    return type1 == type2


def _check_shape_common(actual, expected, name: str):
    """Check that two values have compatible shape/length."""
    if isinstance(actual, np.ndarray):
        shape_actual = actual.shape
        if isinstance(expected, np.ndarray):
            shape_expected = expected.shape
        elif hasattr(expected, '__len__'):
            shape_expected = (len(expected),)
        else:
            shape_expected = ()
        if shape_actual != shape_expected:
            pytest.fail(
                f"Variable `{name}` has incorrect shape: "
                f"{shape_actual} vs {shape_expected}"
            )
    elif hasattr(actual, '__len__') and hasattr(expected, '__len__'):
        if len(actual) != len(expected):
            pytest.fail(
                f"Variable `{name}` has incorrect length: "
                f"{len(actual)} vs {len(expected)}"
            )


# =============================================================================
# Solution Enum
# =============================================================================

class Solution(str, Enum):
    """Enum for solution types."""
    student = "student"
    reference = "reference"


# =============================================================================
# Base Solution Manager
# =============================================================================

class BaseSolutionManager(ABC):
    """
    Base class for managing solution execution and caching.

    Subclasses implement language-specific execution logic.
    """

    def __init__(self, pytestconfig, report_key):
        """
        Initialize the solution manager.

        Args:
            pytestconfig: Pytest configuration object
            report_key: Key to access report in pytestconfig.stash
        """
        self.pytestconfig = pytestconfig
        self.report_key = report_key
        self._report = pytestconfig.stash[report_key]

    @property
    def testsuite(self) -> ComputorTestSuite:
        return self._report["testsuite"]

    @property
    def specification(self) -> ComputorSpecification:
        return self._report["specification"]

    @property
    def report(self) -> ComputorReport:
        return self._report["report"]

    @property
    def solutions(self) -> dict:
        return self._report["solutions"]

    @property
    def root(self) -> str:
        return self._report.get("root", "")

    def get_directory(self, where: Solution) -> str:
        """Get the directory for student or reference solution."""
        if where == Solution.student:
            return self.specification.studentDirectory
        return self.specification.referenceDirectory

    def get_solution(self, idx: int, where: Solution) -> dict:
        """
        Get or compute solution for a test.

        Args:
            idx: Index of the main test
            where: Solution type (student or reference)

        Returns:
            Solution dictionary
        """
        idx_str = str(idx)
        main: ComputorTestCollection = self.testsuite.properties.tests[idx]

        # Return cached solution if available
        if idx_str in self.solutions and where in self.solutions[idx_str]:
            return self.solutions[idx_str][where]

        if idx_str not in self.solutions:
            self.solutions[idx_str] = {}

        # Check dependencies
        error, errormsg, status = self._check_dependencies(idx, where)

        if error:
            self.solutions[idx_str][where] = self._create_error_solution(
                status, errormsg
            )
            return self.solutions[idx_str][where]

        # Execute and get solution
        solution = self._execute_solution(idx, where)
        self.solutions[idx_str][where] = solution

        return solution

    def _check_dependencies(
        self, idx: int, where: Solution
    ) -> Tuple[bool, str, StatusEnum]:
        """
        Check success dependencies for a test.

        Returns:
            Tuple of (has_error, error_message, status)
        """
        main: ComputorTestCollection = self.testsuite.properties.tests[idx]
        success_dependencies = get_property_as_list(main.successDependency)

        for dependency in success_dependencies:
            dep_idx = main_idx_by_dependency(self.testsuite, dependency)
            if dep_idx is None:
                return True, f"Success-Dependency `{dependency}` not valid", StatusEnum.failed

            total = self.report.tests[dep_idx].summary.total
            for sub_idx in range(total):
                result = self.report.tests[dep_idx].tests[sub_idx].result
                if result != ResultEnum.passed:
                    return True, f"Success-Dependency `{dependency}` not satisfied", StatusEnum.skipped

        return False, "", StatusEnum.scheduled

    @abstractmethod
    def _execute_solution(self, idx: int, where: Solution) -> dict:
        """
        Execute code and return solution dictionary.

        Must be implemented by language-specific subclasses.
        """
        pass

    @abstractmethod
    def _create_error_solution(self, status: StatusEnum, errormsg: str) -> dict:
        """
        Create an error solution dictionary.

        Must be implemented by language-specific subclasses.
        """
        pass


# =============================================================================
# Base Test Class
# =============================================================================

class BaseTestClass(ABC):
    """
    Base class for all language-specific test classes.

    Provides common test type handlers and dispatching logic.
    """

    # Override in subclass
    solution_manager_class: type = None

    @abstractmethod
    def get_solution_manager(self, pytestconfig) -> BaseSolutionManager:
        """Get the solution manager for this test class."""
        pass

    @abstractmethod
    def get_report_key(self):
        """Get the report key for accessing pytestconfig.stash."""
        pass

    def test_entrypoint(self, pytestconfig, testcases):
        """
        Execute a single test case.

        Args:
            pytestconfig: Pytest configuration
            testcases: Tuple of (main_idx, sub_idx)
        """
        idx_main, idx_sub = testcases
        context = self._build_test_context(pytestconfig, idx_main, idx_sub)

        # Dispatch to appropriate handler
        testtype = context["testtype"]

        # Common test types
        if testtype == TypeEnum.exist:
            self._test_exist(context)
        elif testtype == TypeEnum.structural:
            self._test_structural(context)
        elif testtype == TypeEnum.error:
            self._test_error(context)
        elif testtype == TypeEnum.warning:
            self._test_warning(context)
        elif testtype == TypeEnum.linting:
            self._test_linting(context)
        else:
            # Language-specific test types
            self._test_language_specific(context)

    def _build_test_context(
        self, pytestconfig, idx_main: int, idx_sub: int
    ) -> Dict[str, Any]:
        """Build the test context dictionary."""
        report_key = self.get_report_key()
        _report = pytestconfig.stash[report_key]
        testsuite: ComputorTestSuite = _report["testsuite"]
        specification: ComputorSpecification = _report["specification"]
        main: ComputorTestCollection = testsuite.properties.tests[idx_main]
        sub: ComputorTest = main.tests[idx_sub]

        return {
            "pytestconfig": pytestconfig,
            "report": _report,
            "testsuite": testsuite,
            "specification": specification,
            "main": main,
            "sub": sub,
            "idx_main": idx_main,
            "idx_sub": idx_sub,
            "testtype": main.type,
            "file": main.file,
            "dir_student": specification.studentDirectory,
            "dir_reference": specification.referenceDirectory,
            # Sub-test properties
            "name": sub.name,
            "value": sub.value,
            "pattern": sub.pattern,
            "qualification": sub.qualification or QualificationEnum.verifyEqual,
            "relative_tolerance": sub.relativeTolerance,
            "absolute_tolerance": sub.absoluteTolerance,
            "allowed_occurance_range": sub.allowedOccuranceRange,
            "type_check": sub.typeCheck,
            "shape_check": sub.shapeCheck,
        }

    def _test_exist(self, context: Dict[str, Any]):
        """Handle exist test type."""
        name = context["name"]
        file = context["file"]
        sub = context["sub"]
        dir_student = context["dir_student"]
        _report = context["report"]

        # When file is set, it IS the file to check; name is just the test identifier
        file_pattern = file if file else name
        student_path = os.path.join(dir_student, file_pattern)
        matches = globlib.glob(student_path)

        if not matches:
            pytest.fail(f"File '{file_pattern}' not found")

        # Check for empty files if allowEmpty is False (default)
        allow_empty = getattr(sub, 'allowEmpty', False)
        if not allow_empty:
            for filepath in matches:
                if os.path.isfile(filepath) and os.path.getsize(filepath) == 0:
                    rel_path = os.path.relpath(filepath, dir_student)
                    pytest.fail(f"File '{rel_path}' is empty (0 bytes)")

        # Store found files for token exchange
        _report.setdefault("student_file_list", []).extend(matches)

    def _test_structural(self, context: Dict[str, Any]):
        """Handle structural test type - override in subclass for language-specific logic."""
        pytest.skip("Structural tests not implemented for this language")

    def _test_error(self, context: Dict[str, Any]):
        """Handle error test type - override in subclass for language-specific logic."""
        pytest.skip("Error tests not implemented for this language")

    def _test_warning(self, context: Dict[str, Any]):
        """Handle warning test type - override in subclass for language-specific logic."""
        pytest.skip("Warning tests not implemented for this language")

    def _test_linting(self, context: Dict[str, Any]):
        """Handle linting test type - override in subclass for language-specific logic."""
        pytest.skip("Linting tests not implemented for this language")

    @abstractmethod
    def _test_language_specific(self, context: Dict[str, Any]):
        """
        Handle language-specific test types.

        Must be implemented by subclasses.
        """
        pass


# =============================================================================
# Compiled Language Base Classes
# =============================================================================

class CompiledSolutionManager(BaseSolutionManager):
    """
    Base solution manager for compiled languages (C, Fortran).

    Handles compilation and execution pattern.
    """

    def _create_error_solution(self, status: StatusEnum, errormsg: str) -> dict:
        return {
            "status": status,
            "errormsg": errormsg,
            "compilation": None,
            "execution": None,
            "stdout": "",
            "stderr": "",
            "exit_code": -1,
        }

    def _create_completed_solution(
        self, comp_result, exec_result, stdout: str, stderr: str, exit_code: int
    ) -> dict:
        return {
            "status": StatusEnum.completed,
            "errormsg": "",
            "compilation": comp_result,
            "execution": exec_result,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
        }


class CompiledTestClass(BaseTestClass):
    """
    Base test class for compiled languages (C, Fortran).

    Provides common handlers for stdio, exitcode, compile tests.
    """

    def _test_stdio(self, context: Dict[str, Any]):
        """Handle stdout/stderr/stdio test types."""
        from ctcore.stdio import compare_outputs

        testtype = context["testtype"]
        sub = context["sub"]
        value = context["value"]
        pattern = context["pattern"]
        qualification = context["qualification"]

        solution_manager = self.get_solution_manager(context["pytestconfig"])
        idx_main = context["idx_main"]

        try:
            student_sol = solution_manager.get_solution(idx_main, Solution.student)
            ref_sol = solution_manager.get_solution(idx_main, Solution.reference)
        except Exception as e:
            pytest.fail(f"Getting solution failed: {e}")

        if student_sol["status"] == StatusEnum.skipped:
            pytest.skip(student_sol["errormsg"])
        elif student_sol["status"] == StatusEnum.timedout:
            pytest.fail(f"Execution timed out: {student_sol['errormsg']}")
        elif student_sol["status"] != StatusEnum.completed:
            pytest.fail(student_sol["errormsg"])

        # Get the appropriate output
        if testtype == TypeEnum.stderr:
            actual = student_sol["stderr"]
            expected = getattr(sub, 'expectedStderr', None) or ref_sol.get("stderr", "")
        else:
            actual = student_sol["stdout"]
            expected = getattr(sub, 'expectedStdout', None) or ref_sol.get("stdout", "")

        # Handle list expected values
        if isinstance(expected, list):
            expected = "\n".join(expected)

        # Use sub.value as expected if provided
        if value is not None:
            if isinstance(value, list):
                expected = "\n".join(str(v) for v in value)
            else:
                expected = str(value)

        # Get comparison options
        ignore_case = getattr(sub, 'ignoreCase', False) or False
        trim_output = getattr(sub, 'trimOutput', True)
        if trim_output is None:
            trim_output = True
        normalize_newlines = getattr(sub, 'normalizeNewlines', True)
        if normalize_newlines is None:
            normalize_newlines = True
        numeric_tolerance = getattr(sub, 'numericTolerance', 1e-6) or 1e-6
        line_number = getattr(sub, 'lineNumber', None)

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
            exit_code=student_sol["exit_code"]
        )

        if not result.success:
            msg = result.message
            if result.actual and result.expected:
                msg += f"\n  Actual: {result.actual[:200]}"
                msg += f"\n  Expected: {result.expected[:200]}"
            pytest.fail(msg)

    def _test_exitcode(self, context: Dict[str, Any]):
        """Handle exitcode test type."""
        from ctcore.stdio import match_exit_code

        sub = context["sub"]
        value = context["value"]

        solution_manager = self.get_solution_manager(context["pytestconfig"])
        idx_main = context["idx_main"]

        try:
            student_sol = solution_manager.get_solution(idx_main, Solution.student)
        except Exception as e:
            pytest.fail(f"Getting solution failed: {e}")

        if student_sol["status"] == StatusEnum.skipped:
            pytest.skip(student_sol["errormsg"])
        elif student_sol["status"] == StatusEnum.timedout:
            pytest.fail("Execution timed out")

        actual_code = student_sol["exit_code"]
        expected_code = getattr(sub, 'expectedExitCode', 0)
        if expected_code is None:
            expected_code = 0

        if value is not None:
            expected_code = int(value)

        result = match_exit_code(actual_code, expected_code)
        if not result.success:
            pytest.fail(f"Exit code mismatch: got {actual_code}, expected {expected_code}")

    def _test_compile(self, context: Dict[str, Any]):
        """Handle compile test type."""
        value = context["value"]
        pattern = context["pattern"]

        solution_manager = self.get_solution_manager(context["pytestconfig"])
        idx_main = context["idx_main"]

        try:
            student_sol = solution_manager.get_solution(idx_main, Solution.student)
        except Exception as e:
            pytest.fail(f"Getting solution failed: {e}")

        comp = student_sol.get("compilation")

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

    def _test_error(self, context: Dict[str, Any]):
        """Handle error test type for compiled languages."""
        pattern = context["pattern"]

        solution_manager = self.get_solution_manager(context["pytestconfig"])
        idx_main = context["idx_main"]

        try:
            student_sol = solution_manager.get_solution(idx_main, Solution.student)
        except Exception as e:
            pytest.fail(f"Getting solution failed: {e}")

        # Check for errors
        has_error = (
            student_sol["status"] in [StatusEnum.failed, StatusEnum.crashed] or
            student_sol["exit_code"] != 0
        )

        if not has_error:
            pytest.fail("Expected an error but execution succeeded")

        # Check error pattern if specified
        if pattern:
            error_output = student_sol["stderr"] + student_sol["errormsg"]
            try:
                if not safe_regex_search(pattern, error_output):
                    pytest.fail(f"Expected error matching `{pattern}` not found")
            except RegexTimeoutError:
                pytest.fail(f"Pattern `{pattern}` timed out (possible ReDoS)")

    def _test_warning(self, context: Dict[str, Any]):
        """Handle warning test type for compiled languages."""
        pattern = context["pattern"]

        solution_manager = self.get_solution_manager(context["pytestconfig"])
        idx_main = context["idx_main"]

        try:
            student_sol = solution_manager.get_solution(idx_main, Solution.student)
        except Exception as e:
            pytest.fail(f"Getting solution failed: {e}")

        comp = student_sol.get("compilation")
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

    def _test_runtime(self, context: Dict[str, Any]):
        """Handle runtime test type."""
        value = context["value"]

        solution_manager = self.get_solution_manager(context["pytestconfig"])
        idx_main = context["idx_main"]

        try:
            student_sol = solution_manager.get_solution(idx_main, Solution.student)
        except Exception as e:
            pytest.fail(f"Getting solution failed: {e}")

        exec_result = student_sol.get("execution")
        if not exec_result:
            pytest.fail("No execution result available")

        # Check execution time limit
        if value is not None:
            max_time = float(value)
            if exec_result.duration > max_time:
                pytest.fail(
                    f"Execution took {exec_result.duration:.3f}s, limit is {max_time}s"
                )


# =============================================================================
# Interpreted Language Base Classes
# =============================================================================

class InterpretedSolutionManager(BaseSolutionManager):
    """
    Base solution manager for interpreted languages (R, Julia, etc.).

    Subclasses set class attributes to customize behavior:
        executor_class: The executor class (e.g., RExecutor, JuliaExecutor)
        execution_error_class: The language-specific execution error
        file_extensions: Glob patterns to find scripts (e.g., ["*.R", "*.r"])
        language_name: Display name for error messages (e.g., "R", "Julia")
    """

    executor_class = None
    execution_error_class = Exception
    file_extensions: List[str] = []
    language_name: str = "Script"

    def _create_error_solution(self, status: StatusEnum, errormsg: str) -> dict:
        return {
            "status": status,
            "errormsg": errormsg,
            "variables": {},
            "errors": [],
            "exectime": 0,
        }

    def _execute_solution(self, idx: int, where) -> dict:
        """Execute script and return solution dict."""
        import glob as _globlib
        import time as _time

        main: ComputorTestCollection = self.testsuite.properties.tests[idx]
        _dir = self.get_directory(where)

        entry_point = main.entryPoint
        timeout = main.timeout or 180.0
        input_answers = get_property_as_list(main.inputAnswers)
        setup_code = get_property_as_list(main.setUpCode)
        teardown_code = get_property_as_list(main.tearDownCode)

        # Apply token exchange
        setup_code = apply_token_exchange_to_code(setup_code, self._report, where)
        teardown_code = apply_token_exchange_to_code(teardown_code, self._report, where)

        # Check setup code dependency
        error, errormsg, status, setup_code = check_setup_code_dependency(
            self.testsuite, self.solutions, main, where, setup_code
        )
        if error:
            return self._create_error_solution(status, errormsg)

        # Find script to execute
        if entry_point:
            script_path = os.path.join(_dir, entry_point)
        else:
            script_path = None
            for ext in self.file_extensions:
                found = _globlib.glob(os.path.join(_dir, ext))
                if found:
                    script_path = found[0]
                    break

            if not script_path:
                return self._create_error_solution(
                    StatusEnum.failed,
                    f"No {self.language_name} script found in {_dir}",
                )

        if not os.path.exists(script_path):
            return self._create_error_solution(
                StatusEnum.failed,
                f"{self.language_name} script not found: {script_path}",
            )

        # Collect variables to extract
        variables_to_extract = []
        for test in main.tests:
            if test.name and main.type in [TypeEnum.variable, TypeEnum.graphics]:
                variables_to_extract.append(test.name)

        # Execute
        try:
            executor = self.executor_class(working_dir=_dir, timeout=timeout)
            start_time = _time.time()

            result = executor.execute_script(
                script_path,
                variables_to_extract=variables_to_extract,
                setup_code=setup_code,
                teardown_code=teardown_code,
                input_answers=input_answers,
            )

            exec_time = _time.time() - start_time

            if result["status"] == "COMPLETED":
                return {
                    "status": StatusEnum.completed,
                    "errormsg": "",
                    "variables": result.get("variables", {}),
                    "errors": result.get("errors", []),
                    "warnings": result.get("warnings", []),
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "exectime": exec_time,
                    "setup_code": setup_code,
                }
            else:
                errors = result.get("errors", ["Unknown error"])
                return {
                    "status": StatusEnum.failed,
                    "errormsg": f"Execution failed: {'; '.join(str(e) for e in errors)}",
                    "variables": result.get("variables", {}),
                    "errors": errors,
                    "exectime": exec_time,
                }

        except self.execution_error_class as e:
            return {
                "status": StatusEnum.failed,
                "errormsg": f"{self.language_name} execution error: {e}",
                "variables": {},
                "errors": [str(e)],
                "exectime": 0,
            }
        except Exception as e:
            return {
                "status": StatusEnum.crashed,
                "errormsg": f"Unexpected error: {e}",
                "variables": {},
                "errors": [str(e)],
                "exectime": 0,
            }


class InterpretedTestClass(BaseTestClass):
    """
    Base test class for interpreted languages (R, Julia, etc.).

    Subclasses set class attributes:
        file_extensions: Glob patterns for structural tests (e.g., ["*.R", "*.r"])
        solution_manager_instance: Cached solution manager (set by get_solution_manager)
    """

    file_extensions: List[str] = []

    def _get_solutions(self, context: Dict[str, Any]) -> Tuple[dict, dict]:
        """Get student and reference solutions, handling errors."""
        solution_manager = self.get_solution_manager(context["pytestconfig"])
        idx_main = context["idx_main"]

        try:
            student_sol = solution_manager.get_solution(idx_main, Solution.student)
            ref_sol = solution_manager.get_solution(idx_main, Solution.reference)
        except Exception as e:
            pytest.fail(f"Getting solution failed: {e}")

        check_solution_status(student_sol)
        return student_sol, ref_sol

    def _test_structural(self, context: Dict[str, Any]):
        """Handle structural test type using file_extensions."""
        sub = context["sub"]
        check_structural(
            name=sub.name,
            pattern=sub.pattern,
            file=context["file"],
            dir_student=context["dir_student"],
            file_extensions=self.file_extensions,
            allowed_occurance_range=sub.allowedOccuranceRange,
            count_requirement=sub.countRequirement,
        )

    def _test_error(self, context: Dict[str, Any]):
        """Handle error test type."""
        sol_student = self._get_student_solution(context)
        check_error(sol_student, context["pattern"])

    def _test_warning(self, context: Dict[str, Any]):
        """Handle warning test type."""
        sol_student = self._get_student_solution(context)
        check_warning(sol_student, context["pattern"])

    def _test_language_specific(self, context: Dict[str, Any]):
        """Handle variable, graphics, and stdout test types."""
        testtype = context["testtype"]

        if testtype in [TypeEnum.variable, TypeEnum.graphics]:
            self._test_variable(context)
        elif testtype == TypeEnum.stdout:
            self._test_stdout(context)
        else:
            pytest.skip(f"Test type `{testtype}` not implemented")

    def _test_variable(self, context: Dict[str, Any]):
        """Handle variable/graphics test type using shared comparison."""
        student_sol, ref_sol = self._get_solutions(context)
        sub = context["sub"]

        student_vars = student_sol.get("variables", {})
        reference_vars = ref_sol.get("variables", {})

        if sub.name not in student_vars:
            pytest.fail(f"Variable '{sub.name}' not found in student solution")

        compare_variable_by_qualification(
            val_student=student_vars[sub.name],
            name=sub.name,
            qualification=sub.qualification,
            pattern=sub.pattern,
            value=sub.value,
            val_reference=reference_vars.get(sub.name),
            relative_tolerance=sub.relativeTolerance,
            absolute_tolerance=sub.absoluteTolerance,
            type_check=sub.typeCheck,
            shape_check=sub.shapeCheck,
            ignore_class=getattr(sub, 'ignoreClass', False),
            count_requirement=sub.countRequirement,
        )

    def _test_stdout(self, context: Dict[str, Any]):
        """Handle stdout test type."""
        student_sol, ref_sol = self._get_solutions(context)
        sub = context["sub"]
        check_stdout(
            student_sol,
            sub.qualification,
            sub.pattern,
            sub.value,
            ref_solution=ref_sol,
        )

    def _get_student_solution(self, context: Dict[str, Any]) -> dict:
        """Get just the student solution."""
        solution_manager = self.get_solution_manager(context["pytestconfig"])
        idx_main = context["idx_main"]
        try:
            sol = solution_manager.get_solution(idx_main, Solution.student)
        except Exception as e:
            pytest.fail(f"Getting solution failed: {e}")
        check_solution_status(sol)
        return sol
