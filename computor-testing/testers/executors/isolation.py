"""Filesystem isolation utilities for student code execution.

Layer 1 of the sandbox refactor: when running student code, copy the
student dir into a tmp dir under ``$TMPDIR`` and run the subprocess
there. Breaks the sibling relationship to the reference dir, which is
what the canonical ``open("../reference/sol.py")`` exploit relies on.

Reference (lecturer-authored) code does NOT go through this — it runs
in its original dir.
"""

import os
import shutil
import tempfile
from contextlib import contextmanager


@contextmanager
def isolated_student_workdir(source_dir: str, script_path: str):
    """Run student code in a throwaway copy of ``source_dir``.

    The reference solution typically lives next to ``source_dir`` (as
    ``../reference``), so a student subprocess running there can do
    ``open("../reference/sol.py")`` and read it. Copying the student
    files into a tmp dir under ``$TMPDIR`` and pointing the subprocess
    at that copy breaks the sibling relationship — the tmp dir has no
    parent the student can traverse to.

    Symlinks in the source dir are deliberately skipped during the copy.
    A symlink in the student dir pointing to the reference would
    otherwise drag the file content along for the ride and defeat the
    whole point.

    Args:
        source_dir: Real student dir on disk (as configured in the
            exercise specification).
        script_path: Path to the student's entry-point script. May be
            absolute or relative to ``source_dir``.

    Yields:
        ``(iso_dir, iso_script_path)`` — the temp dir the subprocess
        should chdir into, and the script's location inside it. Both
        are absolute paths.

    The temp dir is removed on context exit (including on exception).
    """
    def _ignore_symlinks(directory, names):
        return [n for n in names if os.path.islink(os.path.join(directory, n))]

    with tempfile.TemporaryDirectory(prefix="computor_student_") as iso_dir:
        # ``dirs_exist_ok`` lets us copy INTO the empty tmp dir
        # tempfile.TemporaryDirectory created for us.
        shutil.copytree(
            source_dir,
            iso_dir,
            dirs_exist_ok=True,
            symlinks=True,
            ignore=_ignore_symlinks,
        )
        rel = os.path.relpath(script_path, source_dir)
        yield iso_dir, os.path.join(iso_dir, rel)
