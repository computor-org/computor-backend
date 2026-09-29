"""The test harness runs as a bounded, killable process tree (#237).

A fake ``computor-test`` executable stands in for the harness: it leaves a
background ``sleep`` behind, floods its output and hangs. The worker must
time it out, kill everything it started, and keep at most 1 MiB of output.
"""
import asyncio
import os
import stat
import sys
import time

import pytest

from computor_backend.testing import backends
from computor_backend.testing.backends import ComputorTestingBackend, _run_harness

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux-only")

HOSTILE_HARNESS = """#!/bin/sh
sleep 1000 &
echo $! > "{pid_file}"
head -c 50000000 /dev/zero | tr '\\0' 'x'
exec sleep 1000
"""


def _alive(pid: int) -> bool:
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


@pytest.fixture
def hostile_harness(tmp_path):
    pid_file = tmp_path / "pid"
    script = tmp_path / "computor-test"
    script.write_text(HOSTILE_HARNESS.format(pid_file=pid_file))
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script, pid_file


def _assert_dead(pid_file):
    pid = int(pid_file.read_text())
    deadline = time.monotonic() + 5
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not _alive(pid)


def test_harness_timeout_kills_tree(hostile_harness):
    script, pid_file = hostile_harness
    backend = ComputorTestingBackend.__new__(ComputorTestingBackend)
    backend.language = "python"
    start = time.monotonic()
    result = asyncio.run(backend.execute_tests(
        "test.yaml", "spec.yaml", {},
        {"testing_executable": str(script), "timeout_seconds": 3},
    ))
    assert time.monotonic() - start < 20
    assert result["details"] == {"timeout": True}
    _assert_dead(pid_file)


def test_harness_output_is_capped(tmp_path):
    result = _run_harness(
        ["sh", "-c", "head -c 50000000 /dev/zero | tr '\\0' 'x'; "
                     "head -c 50000000 /dev/zero >&2"],
        env=dict(os.environ), timeout=60,
    )
    assert result.returncode == 0
    assert len(result.stdout) == backends._HARNESS_MAX_OUTPUT
    assert len(result.stderr) == backends._HARNESS_MAX_OUTPUT


@pytest.mark.parametrize("script,timeout", [("exit 0", 10), ("sleep 30", 1)])
def test_harness_leader_unreaped_until_group_killed(monkeypatch, script, timeout):
    """No pid-reuse window: the leader (pid == pgid) is still held at killpg."""
    import subprocess
    seen = []
    real_killpg = os.killpg

    def killpg(pgid, sig):
        seen.append(os.path.exists(f"/proc/{pgid}"))
        return real_killpg(pgid, sig)
    monkeypatch.setattr(os, "killpg", killpg)
    try:
        _run_harness(["sh", "-c", script], env=dict(os.environ), timeout=timeout)
    except subprocess.TimeoutExpired:
        assert timeout == 1
    assert seen and all(seen)


# --- testSummary.json ingestion (#237) --------------------------------------

from computor_backend.tasks.temporal_student_testing import (  # noqa: E402
    UnsafeReportError,
    _read_test_report,
)


def test_report_reads_regular_json(tmp_path):
    (tmp_path / "testSummary.json").write_text('{"passed": 3}')
    assert _read_test_report(str(tmp_path), "testSummary.json") == {"passed": 3}


def test_report_symlink_to_worker_file_is_refused(tmp_path):
    secret = tmp_path / "worker_only.json"
    secret.write_text('{"passed": 99, "leak": "TOPSECRET"}')
    out = tmp_path / "out"
    out.mkdir()
    (out / "testSummary.json").symlink_to(secret)
    with pytest.raises(UnsafeReportError, match="symlink"):
        _read_test_report(str(out), "testSummary.json")


def test_report_fifo_does_not_block(tmp_path):
    os.mkfifo(tmp_path / "testSummary.json")
    start = time.monotonic()
    with pytest.raises(UnsafeReportError, match="regular"):
        _read_test_report(str(tmp_path), "testSummary.json")
    assert time.monotonic() - start < 5


def test_report_size_is_capped(tmp_path):
    with open(tmp_path / "testSummary.json", "wb") as f:
        f.truncate(1 << 30)  # 1 GiB, sparse
    with pytest.raises(UnsafeReportError, match="too large"):
        _read_test_report(str(tmp_path), "testSummary.json")
