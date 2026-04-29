"""Filesystem isolation regression tests.

Layer 1 of the sandbox refactor: when student code runs, the subprocess
must NOT be able to reach the reference solution dir via filesystem
traversal (``open("../reference/sol.py")``). The fix runs the student
subprocess inside a copy of the student dir under ``$TMPDIR`` so the
sibling reference dir is gone from the cwd's parent chain.

Tests here exercise the ``isolated_student_workdir`` context manager
directly — they don't boot a full pytest harness because the concern
is purely about the on-disk shape, not test orchestration.
"""

import os
import tempfile
from pathlib import Path

import pytest

from testers.executors.isolation import isolated_student_workdir


@pytest.fixture
def exercise_layout(tmp_path):
    """Build a realistic student/reference layout on disk.

    ::

        $tmp/exercise/
            student/
                main.py
                helper.py
            reference/
                sol.py            <- the secret
    """
    exercise = tmp_path / "exercise"
    student = exercise / "student"
    reference = exercise / "reference"
    student.mkdir(parents=True)
    reference.mkdir(parents=True)

    (reference / "sol.py").write_text("SECRET_REFERENCE = 42\n")
    (student / "main.py").write_text("# student script\n")
    (student / "helper.py").write_text("# auxiliary file the student needs\n")

    return {
        "student": str(student),
        "reference": str(reference),
        "script": str(student / "main.py"),
    }


class TestSiblingReferenceUnreachable:
    """The exact bug from the report: sibling reference dir is gone
    from the parent chain when running inside the iso dir."""

    def test_sibling_reference_visible_without_isolation(self, exercise_layout):
        # Sanity guard for the test itself: confirm the layout is what
        # we think it is (i.e. the bug is reproducible) BEFORE we
        # check the fix.
        ref_via_sibling = os.path.join(
            exercise_layout["student"], "..", "reference", "sol.py"
        )
        assert os.path.exists(ref_via_sibling)

    def test_sibling_reference_unreachable_with_isolation(self, exercise_layout):
        with isolated_student_workdir(
            exercise_layout["student"],
            exercise_layout["script"],
        ) as (iso_dir, _):
            ref_via_sibling = os.path.join(iso_dir, "..", "reference", "sol.py")
            assert not os.path.exists(ref_via_sibling)


class TestStudentFilesPreserved:
    """The student must still see all of their OWN files in the iso
    dir — we're moving the cwd, not stripping content."""

    def test_main_script_readable_in_iso_dir(self, exercise_layout):
        with isolated_student_workdir(
            exercise_layout["student"],
            exercise_layout["script"],
        ) as (_, iso_script):
            assert os.path.exists(iso_script)
            assert "student script" in Path(iso_script).read_text()

    def test_aux_files_copied_too(self, exercise_layout):
        # Helper modules / data files in the student dir must come along
        # — without them, multi-file submissions would break.
        with isolated_student_workdir(
            exercise_layout["student"],
            exercise_layout["script"],
        ) as (iso_dir, _):
            assert (Path(iso_dir) / "helper.py").exists()


class TestSymlinkExfiltrationBlocked:
    """A malicious or misconfigured symlink in the student dir
    pointing OUT to the reference would defeat isolation if we
    naively copied it. The copy step ignores symlinks entirely."""

    def test_symlink_to_reference_is_dropped(self, exercise_layout):
        # Plant a symlink in the student dir pointing at the reference.
        symlink_path = Path(exercise_layout["student"]) / "leaked_solution.py"
        symlink_path.symlink_to(
            Path(exercise_layout["reference"]) / "sol.py"
        )
        assert symlink_path.is_symlink()  # sanity

        with isolated_student_workdir(
            exercise_layout["student"],
            exercise_layout["script"],
        ) as (iso_dir, _):
            # The symlink must not exist in the iso dir, AND its
            # would-be content (the reference solution text) must not
            # be there either.
            iso_payload = Path(iso_dir) / "leaked_solution.py"
            assert not iso_payload.exists()


class TestCleanup:
    """The tmp dir must be wiped on context exit so we don't pile up
    student copies under ``/tmp``."""

    def test_iso_dir_removed_after_context(self, exercise_layout):
        captured = {}
        with isolated_student_workdir(
            exercise_layout["student"],
            exercise_layout["script"],
        ) as (iso_dir, _):
            captured["dir"] = iso_dir
            assert os.path.exists(iso_dir)
        # After the with block exits, the dir is gone.
        assert not os.path.exists(captured["dir"])

    def test_iso_dir_removed_on_exception(self, exercise_layout):
        captured = {}
        with pytest.raises(RuntimeError):
            with isolated_student_workdir(
                exercise_layout["student"],
                exercise_layout["script"],
            ) as (iso_dir, _):
                captured["dir"] = iso_dir
                raise RuntimeError("simulated failure inside the with block")
        # tempfile.TemporaryDirectory cleans up on exception too.
        assert not os.path.exists(captured["dir"])


class TestIsoDirPath:
    """Cosmetic / observability: the iso dir name should make it
    obvious where it came from in case it ever leaks into a log line."""

    def test_iso_dir_has_recognisable_prefix(self, exercise_layout):
        with isolated_student_workdir(
            exercise_layout["student"],
            exercise_layout["script"],
        ) as (iso_dir, _):
            assert os.path.basename(iso_dir).startswith("computor_student_")
