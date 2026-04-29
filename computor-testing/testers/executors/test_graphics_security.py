"""Layer 3 regression tests: the in-process graphics execution path
applies both the import deny-list (Layer 2) and the filesystem
isolation (Layer 1).

The graphics path stays in-process for matplotlib-figure access — a
full subprocess rewrite would need figure serialisation and isn't worth
the cost. Instead we wrap it with the same two protections the
subprocess path already had: AST scan before ``exec``, and a tmp copy
of the student dir as cwd so the sibling reference dir is gone from
the parent chain.

These tests call the graphics function directly with constructed
inputs rather than booting the pytest harness, so they stay fast and
independent of any example assignments in the repo.
"""

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

# Importing test_class triggers heavy conftest-side machinery in the
# package; we want only the function-under-test. Importing the module
# directly works because ``test_class`` has been refactored so the
# graphics function only depends on ``isolation`` + ``sandbox.security``,
# both of which are well-formed standalone modules.
from testers.tests.python.test_class import _execute_graphics_inprocess
from testers.tests.python.conftest import Solution


@pytest.fixture
def exercise_layout(tmp_path):
    """Realistic student/reference layout on disk."""
    exercise = tmp_path / "exercise"
    student = exercise / "student"
    reference = exercise / "reference"
    student.mkdir(parents=True)
    reference.mkdir(parents=True)
    (reference / "sol.py").write_text("SECRET_REFERENCE = 42\n")
    return {
        "student": str(student),
        "reference": str(reference),
        "script": str(student / "main.py"),
    }


def _make_main(testlist=None):
    """Minimal fake ``main`` test-collection object — graphics path
    only reads ``main.tests`` so we don't need the full Pydantic model."""
    return SimpleNamespace(tests=testlist or [])


def _run(script_body: str, exercise_layout, where=Solution.student):
    """Drop ``script_body`` into the student dir and run the graphics
    path against it. Returns the populated ``_solution[where]`` dict."""
    Path(exercise_layout["script"]).write_text(script_body)
    solution = {}
    _execute_graphics_inprocess(
        _solution=solution,
        where=where,
        script_path=exercise_layout["script"],
        _dir=exercise_layout["student"],
        setup_code=[],
        teardown_code=[],
        main=_make_main(),
        plt=None,  # the function tolerates None plt
    )
    return solution[where]


# ---------------------------------------------------------------------------
# Layer 2 wired into graphics
# ---------------------------------------------------------------------------


class TestDenyListAppliedToGraphics:
    def test_canonical_exploit_blocked(self, exercise_layout):
        # Same exploit shape that the subprocess path already blocks —
        # graphics must be no easier to defeat.
        result = _run("import os\nx = 1\n", exercise_layout)
        # The function maps blocked imports to a "Security check failed"
        # error and a failed status (not the regular failed-execution
        # status, but failed nonetheless).
        assert any(
            "Security check failed" in err
            for err in result.get("errors", [])
        )

    def test_clean_graphics_script_runs(self, exercise_layout):
        # No dangerous imports — the script must actually run. We don't
        # actually need matplotlib here; we just need exec to succeed.
        result = _run("answer = 42\n", exercise_layout)
        # Either status `completed` (normal path) or — if matplotlib
        # isn't importable in the test env — exec still completed
        # without our deny-list rejecting it.
        assert "Security check failed" not in str(result.get("errors", []))

    def test_reference_solution_skips_deny_list(self, exercise_layout):
        # Reference is lecturer-authored; ``os`` is allowed. Without
        # the where-based exemption a lecturer that writes
        # ``import os`` in the reference would silently fail every
        # student's test run.
        result = _run(
            "import os\nval = os.path.basename('/tmp/x')\n",
            exercise_layout,
            where=Solution.reference,
        )
        assert "Security check failed" not in str(result.get("errors", []))


# ---------------------------------------------------------------------------
# Layer 1 wired into graphics
# ---------------------------------------------------------------------------


class TestIsolationAppliedToGraphics:
    def test_student_runs_in_isolated_cwd(self, exercise_layout):
        # The student script logs ``os.getcwd()`` … but ``os`` is
        # blocked by Layer 2. Instead inject a setup helper that
        # captures the cwd into a side-channel the test can read.
        captured = {}

        def setup_inject(_solution, where, *args, **kwargs):
            captured["cwd"] = os.getcwd()

        # Easier: write a script that captures __file__ (set by the
        # function) into a global, then check that path is under
        # ``$TMPDIR/computor_student_*`` rather than the original
        # student dir.
        script = "captured_file = __file__\n"
        result = _run(script, exercise_layout)

        captured_file = result["namespace"].get("captured_file")
        assert captured_file is not None
        # Was rebased into the iso dir.
        assert "computor_student_" in captured_file
        # And NOT the original student dir.
        assert exercise_layout["student"] not in captured_file

    def test_reference_runs_in_original_dir(self, exercise_layout):
        # Reference is trusted — no isolation, runs in its own dir.
        # We point ``_dir`` at the reference dir explicitly to model
        # how ``get_solution`` would call us.
        ref_script = str(Path(exercise_layout["reference"]) / "ref_main.py")
        Path(ref_script).write_text("captured_file = __file__\n")

        solution = {}
        _execute_graphics_inprocess(
            _solution=solution,
            where=Solution.reference,
            script_path=ref_script,
            _dir=exercise_layout["reference"],
            setup_code=[],
            teardown_code=[],
            main=_make_main(),
            plt=None,
        )
        captured_file = solution[Solution.reference]["namespace"].get("captured_file")
        assert captured_file is not None
        assert "computor_student_" not in captured_file
        # Stayed in the reference dir.
        assert exercise_layout["reference"] in captured_file
