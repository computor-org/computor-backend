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
