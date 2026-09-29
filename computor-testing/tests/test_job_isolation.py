"""Hostile student jobs stay bounded and isolated (#237).

Each test runs a real hostile snippet through the production executor path
(PyExecutor -> ctexec) and checks the observable outcome: the job is stopped
or its attack fails, and the process running the tests (standing in for the
worker) is unharmed. Linux-only.
"""

import os
import sys
import textwrap
import time

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Linux-only")

PyExecutor = pytest.importorskip("testers.executors.python").PyExecutor

MIB = 1024 * 1024


def run_student(tmp_path, code, variables=(), timeout=30.0):
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    (work / "student.py").write_text(textwrap.dedent(code))
    executor = PyExecutor(working_dir=str(work), timeout=timeout)
    return executor.execute("student.py", list(variables))


def uid_task_count():
    """Tasks (threads included) owned by our UID, as RLIMIT_NPROC counts them."""
    uid, count = os.getuid(), 0
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            if os.stat(f"/proc/{pid}").st_uid == uid:
                count += len(os.listdir(f"/proc/{pid}/task"))
        except OSError:
            pass
    return count


# --- 1. per-job resource limits ---------------------------------------------

def test_numpy_and_matplotlib_work_under_default_limits(tmp_path):
    pytest.importorskip("numpy")
    pytest.importorskip("matplotlib")
    result = run_student(tmp_path, """
        import numpy as np, matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        a = np.random.rand(600, 600)
        fig, ax = plt.subplots()
        ax.plot((a @ a).sum(axis=0))
        fig.savefig("plot.png")
        ok = True
    """, ["ok"])
    assert result.success, result.error_message
    assert result.namespace["ok"] is True
    assert (tmp_path / "work" / "plot.png").stat().st_size > 0


def test_memory_hog_is_stopped(tmp_path):
    result = run_student(tmp_path, """
        hog = []
        while True:
            hog.append(bytearray(64 * 1024 * 1024))
    """)
    # RLIMIT_AS (2 GiB) stops it at once, not the 30 s wall-clock timeout.
    assert not result.success
    assert not result.timed_out
    assert result.duration < 20


def test_cpu_limit_kills_busy_loop(tmp_path, monkeypatch):
    monkeypatch.setenv("COMPUTOR_JOB_CPU_SECONDS", "2")
    start = time.monotonic()
    result = run_student(tmp_path, "while True:\n    pass\n", timeout=60)
    assert not result.success
    # Killed by RLIMIT_CPU (SIGKILL at 2 s CPU), long before the 60 s timeout.
    assert time.monotonic() - start < 20
    assert not result.timed_out


def test_file_size_limit(tmp_path):
    result = run_student(tmp_path, """
        with open("big.bin", "wb") as f:
            for _ in range(200):
                f.write(b"x" * (1024 * 1024))
    """)
    assert not result.success
    assert (tmp_path / "work" / "big.bin").stat().st_size <= 64 * MIB


def test_fork_bomb_is_bounded(tmp_path, monkeypatch):
    # RLIMIT_NPROC counts every task of the UID, so leave the job 40 of them.
    budget = 40
    monkeypatch.setenv("COMPUTOR_JOB_MAX_PROCESSES", str(uid_task_count() + budget))
    result = run_student(tmp_path, """
        import os, signal, time
        pids = []
        refused = False
        for _ in range(5000):
            try:
                pid = os.fork()
            except OSError:
                refused = True
                break
            if pid == 0:
                time.sleep(60)
                os._exit(0)
            pids.append(pid)
        spawned = len(pids)
        for pid in pids:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
    """, ["spawned", "refused"])
    assert result.success, result.error_message
    assert result.namespace["refused"] is True
    assert result.namespace["spawned"] < budget + 20
