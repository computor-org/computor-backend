"""
Main test class for Octave code testing.

This module implements the test execution logic, including:
- Variable comparison tests
- Graphics tests
- Structural tests (keyword counting)
- Linting tests
- File existence tests
"""

import os
import time
import pytest
import numpy as np
from typing import Dict, Any, Optional

from ctcore.models import (
    ComputorSpecification, ComputorTestSuite,
    ComputorTestCollection,
    TypeEnum, QualificationEnum,
    StatusEnum, ResultEnum,
    ComputorReport,
)
from .conftest import report_key, Solution
from ctcore.helpers import get_property_as_list, get_abbr, token_exchange
from testers.executors.octave import (
    OctaveExecutor, run_structural_analysis,
)
from ..test_base import (
    check_file_exists,
    check_solution_status,
    check_exist,
    check_error,
    check_warning,
    compare_variable_by_qualification,
    apply_token_exchange_to_code,
)


def main_idx_by_dependency(testsuite: ComputorTestSuite, dependency) -> Optional[int]:
    """Find main test index by dependency ID (Octave uses 1-based indexing)."""
    for idx_main, main in enumerate(testsuite.properties.tests):
        if main.id is not None and dependency == main.id:
            return idx_main
    try:
        idx = int(dependency)
        if idx > 0 and idx <= len(testsuite.properties.tests):
            return idx - 1
    except Exception:
        pass
    return None


def get_solution(pytestconfig, idx_main: int, where: Solution) -> Dict[str, Any]:
    """
    Get or compute solution for a test.

    Args:
        pytestconfig: Pytest configuration object
        idx_main: Index of the main test
        where: Solution type (student or reference)

    Returns:
        Solution dictionary with namespace, status, errors, etc.
    """
    _report = pytestconfig.stash[report_key]
    solutions = _report["solutions"]
    report: ComputorReport = _report["report"]
    testsuite: ComputorTestSuite = _report["testsuite"]
    specification: ComputorSpecification = _report["specification"]
    main: ComputorTestCollection = testsuite.properties.tests[idx_main]
    idx = str(idx_main)

    if idx not in solutions:
        solutions[idx] = {}

    if where not in solutions[idx]:
        solutions[idx][where] = {
            "namespace": {},
            "timestamp": time.time(),
            "status": StatusEnum.scheduled,
            "errormsg": "",
            "exectime": 0,
            "errors": [],
            "warnings": [],
        }

        _solution = solutions[idx][where]
        _dir = (specification.studentDirectory if where == Solution.student
                else specification.referenceDirectory)

        entry_point = main.entryPoint
        timeout = main.timeout or 180.0
        input_answers = get_property_as_list(main.inputAnswers)
        setup_code = get_property_as_list(main.setUpCode)
        teardown_code = get_property_as_list(main.tearDownCode)
        success_dependencies = get_property_as_list(main.successDependency)
        setup_code_dependency = main.setUpCodeDependency
        store_graphics_artifacts = main.storeGraphicsArtifacts
        if specification.storeGraphicsArtifacts is not None:
            store_graphics_artifacts = specification.storeGraphicsArtifacts

        # Apply token exchange
        setup_code = apply_token_exchange_to_code(setup_code, _report, where)
        teardown_code = apply_token_exchange_to_code(teardown_code, _report, where)

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

        # Check setup code dependency
        if setup_code_dependency is not None and not error:
            _idx = main_idx_by_dependency(testsuite, setup_code_dependency)
            if _idx is None:
                error = True
                errormsg = f"Setup-Code-Dependency `{setup_code_dependency}` not valid"
                status = StatusEnum.failed
            else:
                try:
                    _solution["namespace"] = solutions[str(_idx)][where]["namespace"].copy()
                except Exception:
                    error = True
                    errormsg = f"Setup-Code-Dependency `{setup_code_dependency}` not found"
                    status = StatusEnum.failed

        if not error:
            var_names = [sub.name for sub in main.tests]
            executor = OctaveExecutor(_dir, timeout=timeout)

            if entry_point is not None:
                if not os.path.exists(os.path.join(_dir, entry_point)):
                    if where == Solution.student:
                        error = True
                        errormsg = f"entryPoint {entry_point} not found"
                        status = StatusEnum.failed

            if not error:
                success = executor.execute_file(
                    filename=entry_point,
                    setup_code=setup_code,
                    teardown_code=teardown_code,
                    input_answers=input_answers,
                    variables_to_extract=var_names
                )

                _solution["exectime"] = executor.execution_time

                if not success:
                    if "timed out" in executor.error.lower():
                        errormsg = f"Maximum execution time of {timeout} seconds exceeded"
                        status = StatusEnum.timedout
                    else:
                        errormsg = f"Execution failed: {executor.error}"
                        status = StatusEnum.crashed
                    error = True
                else:
                    _solution["namespace"] = executor.namespace

        if not error:
            status = StatusEnum.completed

        _solution["status"] = status
        _solution["errormsg"] = errormsg

    return solutions[idx][where]


class TestComputorOctave:
    """Main test class for Octave code testing."""

    def test_entrypoint(self, pytestconfig, testcases):
        idx_main, idx_sub = testcases

        _report = pytestconfig.stash[report_key]
        testsuite: ComputorTestSuite = _report["testsuite"]
        specification: ComputorSpecification = _report["specification"]
        main = testsuite.properties.tests[idx_main]
        sub = main.tests[idx_sub]

        dir_reference = specification.referenceDirectory
        dir_student = specification.studentDirectory
        testtype = main.type

        # Variable/Graphics/Error/Warning tests
        if testtype in [
            TypeEnum.variable, TypeEnum.graphics,
            TypeEnum.error, TypeEnum.warning,
            TypeEnum.help, TypeEnum.stdout,
        ]:
            try:
                sol_student = get_solution(pytestconfig, idx_main, Solution.student)
                sol_reference = get_solution(pytestconfig, idx_main, Solution.reference)
            except Exception as e:
                pytest.fail(f"Getting solution failed: {e}")

            check_solution_status(sol_student)

            solution_student = sol_student["namespace"]
            solution_reference = sol_reference["namespace"]

            if sub.name not in solution_student:
                raise KeyError(f"Variable `{sub.name}` not found in student namespace")

            val_student = solution_student[sub.name]

            # Get reference value for verifyEqual
            val_reference = None
            if sub.qualification == QualificationEnum.verifyEqual:
                if sub.evalString is not None:
                    val_reference = solution_reference.get(sub.name)
                    if val_reference is None:
                        pytest.skip(f"Evaluation of `{sub.evalString}` not possible")
                elif sub.name in solution_reference:
                    val_reference = solution_reference[sub.name]

            compare_variable_by_qualification(
                val_student=val_student,
                name=sub.name,
                qualification=sub.qualification,
                pattern=sub.pattern,
                value=sub.value,
                val_reference=val_reference,
                relative_tolerance=sub.relativeTolerance,
                absolute_tolerance=sub.absoluteTolerance,
                type_check=sub.typeCheck,
                shape_check=sub.shapeCheck,
                ignore_class=sub.ignoreClass,
                equal_nan=sub.equalNaN,
                count_requirement=sub.countRequirement,
            )

        # Structural tests (Octave-specific: uses run_structural_analysis)
        elif testtype == TypeEnum.structural:
            if sub.allowedOccuranceRange is None:
                pytest.skip(reason="allowedOccuranceRange not set")

            c_min = sub.allowedOccuranceRange[0]
            c_max = sub.allowedOccuranceRange[1]

            file_list = _report.get("student_file_list", [])
            command_list = _report.get("student_command_list", [])
            actual_file = token_exchange(main.file, file_list, command_list)

            file_path = os.path.join(dir_student, actual_file)
            if not os.path.exists(file_path):
                pytest.fail(f"File `{main.file}` not found in student directory")

            counts = run_structural_analysis(file_path, [sub.name])
            c = counts.get(sub.name, 0)

            if c < c_min:
                raise AssertionError(
                    f"`{sub.name}` found {c} times, minimum required: {c_min}"
                )
            if c > c_max:
                raise AssertionError(
                    f"`{sub.name}` found {c} times, maximum allowed: {c_max}"
                )

        elif testtype == TypeEnum.linting:
            pass  # Octave linting not yet implemented

        elif testtype == TypeEnum.exist:
            # Octave exist checks both student and reference
            # When main.file is set, it IS the file to check; sub.name is just the test identifier
            file_pattern = main.file if main.file else sub.name
            exists_s, files_s = check_file_exists(dir_student, file_pattern)
            exists_r, files_r = check_file_exists(dir_reference, file_pattern)

            if not exists_s:
                pytest.fail(f"File '{file_pattern}' not found in student directory")
            if not exists_r:
                pytest.fail(f"File '{file_pattern}' not found in reference directory")

            allow_empty = getattr(sub, 'allowEmpty', False)
            if not allow_empty:
                for f in files_s:
                    filepath = os.path.join(dir_student, f)
                    if os.path.isfile(filepath) and os.path.getsize(filepath) == 0:
                        pytest.fail(f"File '{f}' is empty (0 bytes)")

            if files_s:
                _report["student_file_list"].extend(files_s)
                _report["student_command_list"].extend(
                    [os.path.splitext(f)[0] for f in files_s]
                )
            if files_r:
                _report["reference_file_list"].extend(files_r)
                _report["reference_command_list"].extend(
                    [os.path.splitext(f)[0] for f in files_r]
                )

        else:
            pytest.skip(reason=f"Test type `{testtype}` not implemented")
