"""Kernel sandbox launcher and command-prefix wiring (#240, #241).

The end-to-end filesystem/network guarantees are verified against a real
worker container in the PR; these unit tests pin the pieces that can be
checked without one: the capability probe, and that the executor prefix is
opt-in and shaped correctly.
"""

import os
import subprocess
import sys

import pytest

from ctexec.base import sandbox_command_prefix, SANDBOX_ENABLE_ENV


def test_prefix_is_empty_by_default(monkeypatch):
    monkeypatch.delenv(SANDBOX_ENABLE_ENV, raising=False)
    assert sandbox_command_prefix("/work") == []


def test_prefix_wraps_when_enabled(monkeypatch):
    monkeypatch.setenv(SANDBOX_ENABLE_ENV, "1")
    prefix = sandbox_command_prefix("/work", rw_paths=["/scratch"], ro_paths=["/ref"])
    assert prefix[0] == sys.executable
    assert prefix[1:4] == ["-m", "sandbox.launch", "--required"]
    assert "--workdir" in prefix and "/work" in prefix
    assert prefix[prefix.index("--rw") + 1] == "/scratch"
    assert prefix[prefix.index("--ro") + 1] == "/ref"
    assert prefix[-1] == "--"


def test_prefix_off_for_any_other_value(monkeypatch):
    monkeypatch.setenv(SANDBOX_ENABLE_ENV, "0")
    assert sandbox_command_prefix("/work") == []


@pytest.mark.skipif(sys.platform != "linux", reason="Landlock is Linux-only")
def test_probe_reports_landlock():
    out = subprocess.check_output(
        [sys.executable, "-m", "sandbox.launch", "--probe"], text=True
    )
    import json
    report = json.loads(out)
    assert "landlock_abi" in report
    assert "netns" in report


@pytest.mark.skipif(sys.platform != "linux", reason="Landlock is Linux-only")
def test_landlock_blocks_reads_outside_allowlist(tmp_path):
    if os.environ.get("COMPUTOR_SANDBOX_DISABLE") == "1":
        pytest.skip("sandbox explicitly disabled")
    secret = tmp_path / "secret.txt"
    secret.write_text("master solution")
    work = tmp_path / "work"
    work.mkdir()

    probe = (
        "import sys;\n"
        "open(sys.argv[1]).read();\n"
        "print('READ')\n"
    )
    result = subprocess.run(
        [sys.executable, "-m", "sandbox.launch", "--required",
         "--workdir", str(work), "--",
         sys.executable, "-c", probe, str(secret)],
        capture_output=True, text=True,
    )
    # The secret sits outside every bound path, so the read must fail.
    if result.returncode == 125:
        pytest.skip("Landlock unavailable on this host")
    assert result.returncode != 0
    assert "READ" not in result.stdout
    assert "PermissionError" in result.stderr or "Permission denied" in result.stderr
