"""
Python Testing Framework - Test Class

Main test execution logic for Python code testing.
"""

import glob as globlib
import io
import os
import re
import sys
import time
import random
import token
import tokenize
from contextlib import nullcontext
import pytest
import numpy as np

from ctcore.models import (
    ComputorTestSuite,
    ComputorTestCollection,
    ComputorSpecification,
    ComputorReport,
    TypeEnum,
    StatusEnum,
    QualificationEnum,
)
from .conftest import report_key, Solution
from ctcore.helpers import get_property_as_list, token_exchange
from testers.executors.python import PyExecutor, PyExecutionError
from testers.executors.isolation import isolated_student_workdir
from ..test_base import (
    main_idx_by_dependency,
    check_success_dependencies,
    check_setup_code_dependency,
    apply_token_exchange_to_code,
    check_solution_status,
    check_exist,
    check_error,
    check_warning,
    compare_variable_by_qualification,
)


def get_solution(mm, pytestconfig, idx: int, where: Solution) -> dict:
    """
    Get or compute solution for a test.

    Executes Python code if not already cached.
    """
    _report = pytestconfig.stash[report_key]
    testsuite: ComputorTestSuite = _report["testsuite"]
    specification: ComputorSpecification = _report["specification"]
    report: ComputorReport = _report["report"]
    solutions = _report["solutions"]

    idx_str = str(idx)
    main: ComputorTestCollection = testsuite.properties.tests[idx]

    if idx_str in solutions and where in solutions[idx_str]:
        return solutions[idx_str][where]

    if idx_str not in solutions:
        solutions[idx_str] = {}

    _solution = solutions[idx_str]
    _dir = (specification.studentDirectory if where == Solution.student
            else specification.referenceDirectory)

    entry_point = main.entryPoint
    timeout = main.timeout or 180.0
    input_answers = get_property_as_list(main.inputAnswers)
    setup_code = get_property_as_list(main.setUpCode)
    teardown_code = get_property_as_list(main.tearDownCode)

    # Apply token exchange
    setup_code = apply_token_exchange_to_code(setup_code, _report, where)
    teardown_code = apply_token_exchange_to_code(teardown_code, _report, where)

    # Check dependencies
    error, errormsg, status = check_success_dependencies(testsuite, report, main)

    if not error:
        error, errormsg, status, setup_code = check_setup_code_dependency(
            testsuite, solutions, main, where, setup_code
        )

    _error_solution = {
        "status": status,
        "errormsg": errormsg,
        "namespace": {},
        "variables": {},
        "errors": [],
        "traceback": {},
        "exectime": 0,
        "std": {"stdout": None, "stderr": None},
    }

    if error:
        _solution[where] = _error_solution
        return _solution[where]

    # Determine the Python script to execute
    if entry_point:
        script_path = os.path.join(_dir, entry_point)
    else:
        py_files = globlib.glob(os.path.join(_dir, "*.py"))
        if py_files:
            script_path = py_files[0]
        else:
            _error_solution["status"] = StatusEnum.failed
            _error_solution["errormsg"] = f"No Python script found in {_dir}"
            _error_solution["errors"] = [f"No .py files in {_dir}"]
            _solution[where] = _error_solution
            return _solution[where]

    if not os.path.exists(script_path):
        if where == Solution.student:
            _error_solution["status"] = StatusEnum.failed
            _error_solution["errormsg"] = f"Python script not found: {script_path}"
            _error_solution["errors"] = [f"File not found: {script_path}"]
            _solution[where] = _error_solution
            return _solution[where]
        else:
            _solution[where] = {
                "status": StatusEnum.completed, "errormsg": "",
                "namespace": {}, "variables": {}, "errors": [],
                "traceback": {}, "exectime": 0,
                "std": {"stdout": None, "stderr": None},
            }
            return _solution[where]

    # Collect variables/expressions to extract
    variables_to_extract = []
    for test in main.tests:
        if test.name and main.type in [TypeEnum.variable, TypeEnum.graphics, TypeEnum.stdout]:
            variables_to_extract.append(test.name)
            base_name = test.name.split('[')[0].split('.')[0]
            if base_name not in variables_to_extract:
                variables_to_extract.append(base_name)

    # Override matplotlib show
    try:
        from matplotlib import pyplot as plt
        mm.setattr(plt, "show", lambda *x: None)
    except ImportError:
        plt = None

    # Set up input answers
    if input_answers:
        mm.setattr('sys.stdin', io.StringIO("\n".join(input_answers)))

    # Seed random for reproducibility
    random.seed(1)
    np.random.seed(1)

    # Graphics tests require in-process execution to access matplotlib figures
    if main.type == TypeEnum.graphics:
        _execute_graphics_inprocess(
            _solution, where, script_path, _dir, setup_code, teardown_code,
            main, plt
        )
    else:
        _execute_subprocess(
            _solution, where, script_path, _dir, timeout,
            variables_to_extract, setup_code, teardown_code, input_answers
        )

    mm.undo()
    return _solution[where]


def _execute_graphics_inprocess(
    _solution, where, script_path, _dir, setup_code, teardown_code, main, plt
):
    """Execute Python code in-process for graphics tests."""
    try:
        start_time = time.time()
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        namespace = {'__file__': script_path}
        old_stdout, old_stderr, old_cwd = sys.stdout, sys.stderr, os.getcwd()

        try:
            os.chdir(_dir)
            if _dir not in sys.path:
                sys.path.insert(0, _dir)
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            with open(script_path, 'r') as f:
                code = f.read()
            exec(compile(code, script_path, 'exec'), namespace)

            for code in setup_code:
                exec(code, namespace)
            for code in teardown_code:
                exec(code, namespace)

            # Extract graphics objects
            try:
                from matplotlib import pyplot as plt_mod
                namespace['plt'] = plt_mod
            except ImportError:
                pass

            namespace["_graphics_object_"] = {}
            for test in main.tests:
                fun2eval = f"plt.{test.name}"
                try:
                    namespace["_graphics_object_"][test.name] = eval(fun2eval, namespace)
                except (AttributeError, NameError, SyntaxError, KeyError):
                    pass

            _solution[where] = {
                "status": StatusEnum.completed, "errormsg": "",
                "namespace": namespace, "variables": namespace,
                "errors": [], "warnings": [], "traceback": {},
                "exectime": time.time() - start_time,
                "setup_code": setup_code,
                "std": {"stdout": stdout_capture.getvalue(), "stderr": stderr_capture.getvalue()},
            }
        except Exception as e:
            import traceback as tb
            _solution[where] = {
                "status": StatusEnum.failed,
                "errormsg": f"Execution failed: {e}",
                "namespace": namespace, "variables": namespace,
                "errors": [str(e)], "traceback": {"error": str(e)},
                "exectime": time.time() - start_time,
                "std": {"stdout": stdout_capture.getvalue(), "stderr": stderr_capture.getvalue()},
            }
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
            os.chdir(old_cwd)
            if plt:
                plt.close('all')
    except Exception as e:
        _solution[where] = {
            "status": StatusEnum.crashed, "errormsg": f"Unexpected error: {e}",
            "namespace": {}, "variables": {}, "errors": [str(e)],
            "traceback": {}, "exectime": 0,
            "std": {"stdout": None, "stderr": None},
        }


def _execute_subprocess(
    _solution, where, script_path, _dir, timeout,
    variables_to_extract, setup_code, teardown_code, input_answers
):
    """Execute Python code via subprocess.

    For student code, the subprocess is jailed to a copy of the student
    dir living under ``$TMPDIR`` — no sibling reference dir to traverse
    to. Reference solutions run in their original dir (they're trusted).
    """
    is_student = where == Solution.student

    # Student code -> isolated copy; reference code -> original dir.
    if is_student:
        ctx = isolated_student_workdir(_dir, script_path)
    else:
        ctx = nullcontext((_dir, script_path))

    try:
        with ctx as (run_dir, run_script):
            executor = PyExecutor(
                working_dir=run_dir,
                timeout=timeout,
                security_check=is_student,
            )
            start_time = time.time()

            result = executor.execute_script(
                run_script,
                variables_to_extract=variables_to_extract,
                setup_code=setup_code,
                teardown_code=teardown_code,
                input_answers=input_answers,
            )

        exec_time = time.time() - start_time

        if result["status"] == "COMPLETED":
            _solution[where] = {
                "status": StatusEnum.completed, "errormsg": "",
                "namespace": result.get("variables", {}),
                "variables": result.get("variables", {}),
                "errors": result.get("errors", []),
                "warnings": result.get("warnings", []),
                "traceback": result.get("traceback", {}),
                "exectime": exec_time, "setup_code": setup_code,
                "std": {"stdout": result.get("stdout", ""), "stderr": result.get("stderr", "")},
            }
        else:
            errors = result.get("errors", ["Unknown error"])
            _solution[where] = {
                "status": StatusEnum.failed,
                "errormsg": f"Execution failed: {'; '.join(str(e) for e in errors)}",
                "namespace": result.get("variables", {}),
                "variables": result.get("variables", {}),
                "errors": errors,
                "traceback": result.get("traceback", {}),
                "exectime": exec_time,
                "std": {"stdout": result.get("stdout", ""), "stderr": result.get("stderr", "")},
            }
    except PyExecutionError as e:
        _solution[where] = {
            "status": StatusEnum.failed, "errormsg": f"Python execution error: {e}",
            "namespace": {}, "variables": {}, "errors": [str(e)],
            "traceback": {}, "exectime": 0,
            "std": {"stdout": None, "stderr": None},
        }
    except Exception as e:
        _solution[where] = {
            "status": StatusEnum.crashed, "errormsg": f"Unexpected error: {e}",
            "namespace": {}, "variables": {}, "errors": [str(e)],
            "traceback": {}, "exectime": 0,
            "std": {"stdout": None, "stderr": None},
        }


class TestComputorPython:
    """Main test class for Python code testing."""

    def test_entrypoint(self, pytestconfig, monkeymodule, testcases):
        idx_main, idx_sub = testcases

        _report = pytestconfig.stash[report_key]
        testsuite: ComputorTestSuite = _report["testsuite"]
        specification: ComputorSpecification = _report["specification"]
        main = testsuite.properties.tests[idx_main]
        sub = main.tests[idx_sub]

        dir_student = specification.studentDirectory
        testtype = main.type

        # Variable/Graphics/Stdout tests
        if testtype in [TypeEnum.variable, TypeEnum.graphics, TypeEnum.stdout]:
            try:
                sol_student = get_solution(monkeymodule, pytestconfig, idx_main, Solution.student)
                sol_reference = get_solution(monkeymodule, pytestconfig, idx_main, Solution.reference)
            except Exception as e:
                pytest.fail(f"Getting solution failed: {e}")

            check_solution_status(sol_student)

            solution_student = sol_student.get("namespace", {})
            solution_reference = sol_reference.get("namespace", {})

            # For graphics tests, use _graphics_object_ namespace
            if testtype == TypeEnum.graphics:
                solution_student = solution_student.get("_graphics_object_", {})
                solution_reference = solution_reference.get("_graphics_object_", {})

            # Get student value
            if testtype == TypeEnum.stdout:
                val_student = sol_student["std"]["stdout"]
            elif sub.name in solution_student:
                val_student = solution_student[sub.name]
            else:
                try:
                    val_student = eval(sub.name, solution_student)
                except Exception:
                    pytest.fail(f"Variable `{sub.name}` not found in student namespace")

            # Get reference value for verifyEqual
            val_reference = None
            if sub.qualification == QualificationEnum.verifyEqual:
                if sub.evalString is not None:
                    try:
                        val_reference = eval(sub.evalString, solution_reference)
                    except Exception:
                        pytest.skip(f"Evaluation of `{sub.evalString}` not possible")
                elif testtype == TypeEnum.stdout:
                    val_reference = sol_reference["std"]["stdout"]
                elif sub.name in solution_reference:
                    val_reference = solution_reference[sub.name]
                else:
                    try:
                        val_reference = eval(sub.name, solution_reference)
                    except Exception:
                        pytest.skip(f"Variable `{sub.name}` not found in reference")

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
                count_requirement=sub.countRequirement,
            )

        elif testtype == TypeEnum.exist:
            # Python exist test: file pattern from main.file or sub.name
            if main.file:
                file_pattern = main.file
            elif sub.name and sub.name != '-':
                file_pattern = sub.name
            else:
                pytest.skip("No file pattern specified for exist test")

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

            _report["student_file_list"].extend(matches)

        elif testtype == TypeEnum.structural:
            # Python-specific: uses tokenizer
            if main.file:
                file_path = os.path.join(dir_student, main.file)
            else:
                py_files = globlib.glob(os.path.join(dir_student, "*.py"))
                file_path = py_files[0] if py_files else None

            if not file_path or not os.path.exists(file_path):
                pytest.fail("Python file not found for structural test")

            if sub.allowedOccuranceRange is None:
                pytest.skip("allowedOccuranceRange not set")

            c_min, c_max = sub.allowedOccuranceRange
            if c_max == 0:
                c_max = float('inf')

            count = 0
            with open(file_path, 'rb') as f:
                tokens = tokenize.tokenize(f.readline)
                for _token in tokens:
                    if sub.occuranceType:
                        c_type = getattr(token, sub.occuranceType, None)
                        if c_type and _token.type == c_type and _token.string == sub.name:
                            count += 1
                    else:
                        if _token.string == sub.name:
                            count += 1

            assert c_min <= count <= c_max, \
                f"`{sub.name}` found {count} times, expected {c_min}-{c_max}"

        elif testtype == TypeEnum.linting:
            # Python-specific: flake8
            import subprocess

            if main.file:
                file_path = os.path.join(dir_student, main.file)
            else:
                py_files = globlib.glob(os.path.join(dir_student, "*.py"))
                file_path = py_files[0] if py_files else None

            if not file_path or not os.path.exists(file_path):
                pytest.fail("Python file not found for linting")

            ignore_pattern = sub.pattern or ""
            result = subprocess.run(
                ['python', '-m', 'flake8', file_path, f'--ignore={ignore_pattern}'],
                capture_output=True, text=True
            )

            if result.stdout:
                lines = result.stdout.strip().split('\n')
                error_count = len([l for l in lines if l])
                if error_count > 0:
                    pytest.fail(f"{error_count} linting errors in `{main.file}`")

        elif testtype == TypeEnum.error:
            sol_student = get_solution(monkeymodule, pytestconfig, idx_main, Solution.student)
            check_error(sol_student, sub.pattern)

        elif testtype == TypeEnum.warning:
            sol_student = get_solution(monkeymodule, pytestconfig, idx_main, Solution.student)
            check_warning(sol_student, sub.pattern)

        else:
            pytest.skip(f"Unknown test type: {testtype}")
