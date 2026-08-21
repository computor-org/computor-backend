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
    check_occurrence_range,
)
from ctcore.security import safe_regex_findall, RegexTimeoutError


# Token types that carry no code and must never take part in a name match.
# COMMENT/STRING/FSTRING_* exclusion keeps matches out of comments and literals.
_NEEDLE_SKIP_TYPES = {
    tokenize.ENCODING, tokenize.NEWLINE, tokenize.NL, tokenize.INDENT,
    tokenize.DEDENT, tokenize.ENDMARKER, tokenize.COMMENT,
}
_HAYSTACK_SKIP_TYPES = {
    tokenize.ENCODING, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT,
    tokenize.STRING, tokenize.ENDMARKER,
} | {
    t for t in (
        # FSTRING_* only exist on Python 3.12+
        getattr(tokenize, _n, None)
        for _n in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END")
    )
    if t is not None
}


def _tokenize_name(name: str):
    """
    Tokenize a searched-for name into its significant token strings.

    "for" -> ["for"], "np.pi" -> ["np", ".", "pi"].
    Returns None if the name is not tokenizable Python.
    """
    try:
        pieces = [
            t.string for t in tokenize.generate_tokens(io.StringIO(name).readline)
            if t.type not in _NEEDLE_SKIP_TYPES and t.string
        ]
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return None
    return pieces or None


def _read_tokens(file_path: str):
    """Tokenize a student file, failing the test if it cannot be parsed."""
    try:
        with open(file_path, 'rb') as f:
            return list(tokenize.tokenize(f.readline))
    except (tokenize.TokenError, SyntaxError, IndentationError) as e:
        pytest.fail(f"Could not tokenize student file: {e}")


def _count_single_token(file_path: str, name: str, occurance_type=None) -> int:
    """Count tokens whose text equals `name`, optionally filtered by token type."""
    count = 0
    for _token in _read_tokens(file_path):
        if occurance_type:
            c_type = getattr(token, occurance_type, None)
            if c_type and _token.type == c_type and _token.string == name:
                count += 1
        elif _token.type not in _HAYSTACK_SKIP_TYPES and _token.string == name:
            count += 1
    return count


def _count_token_sequence(file_path: str, name: str) -> int:
    """
    Count non-overlapping occurrences of `name` as a token sequence.

    Multi-token names such as "np.pi" are matched as consecutive tokens, which
    plain per-token comparison can never do. NEWLINE/NL are kept in the stream
    so a sequence cannot span logical lines.
    """
    needle = _tokenize_name(name)
    if needle is None:
        return _count_single_token(file_path, name)
    if len(needle) == 1:
        return _count_single_token(file_path, needle[0])

    hay = [
        t.string for t in _read_tokens(file_path)
        if t.type not in _HAYSTACK_SKIP_TYPES
    ]

    count = 0
    i = 0
    while i <= len(hay) - len(needle):
        if hay[i:i + len(needle)] == needle:
            count += 1
            i += len(needle)
        else:
            i += 1
    return count


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
        store_graphics_artifacts = main.storeGraphicsArtifacts
        if specification.storeGraphicsArtifacts is not None:
            store_graphics_artifacts = specification.storeGraphicsArtifacts
        artifact_dir = (
            specification.artifactDirectory
            if store_graphics_artifacts and specification.artifactDirectory
            else None
        )
        _execute_graphics_inprocess(
            _solution, where, script_path, _dir, setup_code, teardown_code,
            main, plt,
            artifact_dir=artifact_dir,
            artifact_prefix=f"{where}_test_{idx}",
        )
    else:
        _execute_subprocess(
            _solution, where, script_path, _dir, timeout,
            variables_to_extract, setup_code, teardown_code, input_answers
        )

    mm.undo()
    return _solution[where]


def _execute_graphics_inprocess(
    _solution, where, script_path, _dir, setup_code, teardown_code, main, plt,
    artifact_dir=None, artifact_prefix="",
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
                plt_mod = None

            namespace["_graphics_object_"] = {}
            for test in main.tests:
                fun2eval = f"plt.{test.name}"
                try:
                    namespace["_graphics_object_"][test.name] = eval(fun2eval, namespace)
                except (AttributeError, NameError, SyntaxError, KeyError):
                    pass

            # Persist the open figures as result artifacts while they are
            # still alive — plt.close('all') in the finally wipes them.
            if artifact_dir and plt_mod is not None:
                for fig_num in plt_mod.get_fignums():
                    try:
                        plt_mod.figure(fig_num).savefig(os.path.join(
                            artifact_dir,
                            f"{artifact_prefix}_figure_{fig_num}.png",
                        ))
                    except Exception as e:
                        print(f"Warning: could not save figure {fig_num}: {e}",
                              file=sys.stderr)

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
    """Execute Python code via subprocess."""
    try:
        executor = PyExecutor(working_dir=_dir, timeout=timeout)
        start_time = time.time()

        result = executor.execute_script(
            script_path,
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

            if sub.allowedOccuranceRange is None and sub.countRequirement is None:
                pytest.skip("allowedOccuranceRange not set")

            if sub.pattern:
                with open(file_path, 'r') as f:
                    source = f.read()
                try:
                    count = len(safe_regex_findall(sub.pattern, source))
                except RegexTimeoutError:
                    pytest.fail(f"Pattern `{sub.pattern}` timed out (possible ReDoS)")
            elif sub.occuranceType:
                count = _count_single_token(
                    file_path, sub.name, occurance_type=sub.occuranceType
                )
            else:
                count = _count_token_sequence(file_path, sub.name)

            if sub.allowedOccuranceRange is not None:
                check_occurrence_range(
                    count, sub.allowedOccuranceRange, f"`{sub.name}`"
                )
            elif count != sub.countRequirement:
                pytest.fail(
                    f"`{sub.name}` found {count} times, "
                    f"expected {sub.countRequirement}"
                )

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
