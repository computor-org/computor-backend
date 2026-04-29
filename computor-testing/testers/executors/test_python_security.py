"""Security regression tests for the Python tester.

Covers Layer 2 of the sandbox refactor: the import deny-list is now
default-on for student code and gates the canonical "read the reference
solution via ``import os``" exploit.

Three concerns:

1. The deny-list catches the obvious exploit shapes the AST scanner is
   designed for (``import``, ``from ... import``, ``__import__``).
2. ``PyExecutor`` returns a ``BLOCKED`` status (and skips actually
   executing the script) when the deny-list fires, so the framework
   surfaces the security failure as a normal test failure rather than
   silently letting the subprocess run.
3. The default applies to student code only; reference solutions
   (lecturer-authored) are exempt at the call site, and a course-wide
   env-var escape hatch turns the default off.

These tests don't boot a full pytest harness — they exercise
``PyExecutor`` directly with throwaway scripts on disk so they stay
fast and don't depend on the example assignments in the repo.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sandbox.security import check_dangerous_imports
from testers.executors.python import (
    PyExecutor,
    _security_check_disabled_via_env,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_script(working_dir: Path, body: str, name: str = "student.py") -> str:
    """Write a script into a working dir and return its absolute path."""
    path = working_dir / name
    path.write_text(body)
    return str(path)


@pytest.fixture
def working_dir(tmp_path) -> Path:
    """Per-test isolated working dir on the real filesystem.

    The PyExecutor shells out to a real Python subprocess, so we need a
    real dir on disk that the subprocess can chdir into.
    """
    return tmp_path


# ---------------------------------------------------------------------------
# AST scanner correctness
# ---------------------------------------------------------------------------


class TestDenyListAstScanner:
    """The scanner catches every shape the canonical reference-leak
    exploit can take. It's not airtight (a determined attacker can
    bypass via ``getattr(__builtins__, '__import__')``) but it closes
    the obvious paths."""

    def test_plain_import_blocked(self):
        issues = check_dangerous_imports("import os")
        assert any("os" in i.message for i in issues)

    def test_from_import_blocked(self):
        issues = check_dangerous_imports("from os import path")
        assert any("os" in i.message for i in issues)

    def test_dotted_from_import_blocked(self):
        # ``from os.path import join`` — top-level package is the
        # checked unit, so this still trips.
        issues = check_dangerous_imports("from os.path import join")
        assert any("os" in i.message for i in issues)

    def test_dunder_import_call_blocked(self):
        issues = check_dangerous_imports("x = __import__('os')")
        assert any("__import__" in i.message for i in issues)

    def test_subprocess_blocked(self):
        # subprocess shells out — a reverse shell vector if exposed.
        issues = check_dangerous_imports("import subprocess")
        assert any("subprocess" in i.message for i in issues)

    def test_pathlib_blocked(self):
        # pathlib gives the same filesystem reach as os without the
        # name. Treat it the same.
        issues = check_dangerous_imports("from pathlib import Path")
        assert any("pathlib" in i.message for i in issues)

    def test_legitimate_imports_pass(self):
        # The scanner must not false-positive on stdlib that's
        # routinely used in introductory exercises.
        for code in (
            "import math",
            "import json",
            "from collections import Counter",
            "import numpy as np",
            "import re",
        ):
            assert check_dangerous_imports(code) == [], code


# ---------------------------------------------------------------------------
# PyExecutor BLOCKED status
# ---------------------------------------------------------------------------


class TestPyExecutorBlocksStudentExploit:
    """End-to-end: ``execute_script`` returns BLOCKED instead of
    spawning the subprocess when the script trips the deny-list."""

    def test_canonical_exploit_returns_blocked(self, working_dir):
        # The exact attack from the bug report.
        script = _write_script(working_dir, (
            "import os\n"
            "for f in os.listdir('.'):\n"
            "    print(f)\n"
        ))
        executor = PyExecutor(working_dir=str(working_dir))
        result = executor.execute_script(script)

        assert result["status"] == "BLOCKED"
        assert any("os" in err for err in result["errors"])
        # No code ran — these stay empty.
        assert result["stdout"] == ""
        assert result["variables"] == {}

    def test_clean_script_runs_normally(self, working_dir):
        # The deny-list mustn't break ordinary student code.
        script = _write_script(working_dir, "answer = 42\n")
        executor = PyExecutor(working_dir=str(working_dir))
        result = executor.execute_script(script, variables_to_extract=["answer"])

        assert result["status"] == "COMPLETED"
        assert result["variables"].get("answer") == 42

    def test_security_check_off_skips_blocking(self, working_dir):
        # Reference solutions go through this path. They're trusted, so
        # the deny-list must not stop them — even if they import ``os``.
        script = _write_script(working_dir, (
            "import os\n"
            "answer = os.path.basename('/tmp/x')\n"
        ))
        executor = PyExecutor(
            working_dir=str(working_dir),
            security_check=False,
        )
        result = executor.execute_script(script, variables_to_extract=["answer"])

        assert result["status"] == "COMPLETED"
        assert result["variables"].get("answer") == "x"


# ---------------------------------------------------------------------------
# Env-var escape hatch
# ---------------------------------------------------------------------------


class TestEnvVarOverride:
    """Course-wide opt-out: when
    ``COMPUTOR_TESTING_DISABLE_SECURITY_CHECK=1`` is set, the
    deny-list is off everywhere even when the caller asks for it.
    Lets a curriculum that legitimately teaches ``os`` / ``pathlib``
    run unblocked."""

    @pytest.mark.parametrize("val", ["1", "true", "TRUE", "yes", "on"])
    def test_truthy_values_disable(self, val):
        with patch.dict(os.environ, {"COMPUTOR_TESTING_DISABLE_SECURITY_CHECK": val}):
            assert _security_check_disabled_via_env() is True

    @pytest.mark.parametrize("val", ["", "0", "false", "off", "no"])
    def test_falsy_or_unset_keeps_default(self, val):
        with patch.dict(os.environ, {"COMPUTOR_TESTING_DISABLE_SECURITY_CHECK": val}):
            assert _security_check_disabled_via_env() is False

    def test_unset_keeps_default(self, monkeypatch):
        monkeypatch.delenv("COMPUTOR_TESTING_DISABLE_SECURITY_CHECK", raising=False)
        assert _security_check_disabled_via_env() is False

    def test_executor_constructor_honours_env(self, monkeypatch):
        # Caller asks for security_check=True, but the env says off:
        # env wins. (So a course can flip it once and not have to chase
        # every caller.)
        monkeypatch.setenv("COMPUTOR_TESTING_DISABLE_SECURITY_CHECK", "1")
        executor = PyExecutor(security_check=True)
        assert executor.security_check is False
