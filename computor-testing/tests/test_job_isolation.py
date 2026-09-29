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


@pytest.fixture(autouse=True)
def _nproc_headroom(monkeypatch):
    """RLIMIT_NPROC is UID-wide; on a developer box the login session alone
    can exceed the 512 default. Give each job the default-sized headroom above
    what the UID already runs, as a dedicated worker UID would have."""
    monkeypatch.setenv("COMPUTOR_JOB_MAX_PROCESSES", str(uid_task_count() + 256))


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


# --- 2. process-tree teardown -----------------------------------------------

SPAWN_DESCENDANTS = textwrap.dedent("""
    import os, subprocess, time
    detached = subprocess.Popen(["sleep", "1000"])  # never waited for
    r, w = os.pipe()
    if os.fork() == 0:                              # double fork: the
        if os.fork() == 0:                          # grandchild is orphaned
            os.write(w, str(os.getpid()).encode())
            time.sleep(1000)
        os._exit(0)
    grandchild = int(os.read(r, 32))
    with open("pids.txt", "w") as f:
        f.write(f"{detached.pid} {grandchild}")
""")


def alive(pid):
    """True if pid exists and is not a zombie awaiting its reaper."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            return f.read().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


def assert_all_dead(pid_file):
    pids = [int(p) for p in pid_file.read_text().split()]
    assert len(pids) == 2
    deadline = time.monotonic() + 5
    while any(alive(p) for p in pids) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not [p for p in pids if alive(p)]


def test_descendants_killed_on_timeout(tmp_path):
    result = run_student(tmp_path, SPAWN_DESCENDANTS + "time.sleep(1000)\n",
                         timeout=3)
    assert result.timed_out
    assert_all_dead(tmp_path / "work" / "pids.txt")


def test_descendants_killed_when_job_finishes(tmp_path):
    result = run_student(tmp_path, SPAWN_DESCENDANTS + "done = True\n", ["done"])
    assert result.success, result.error_message
    assert_all_dead(tmp_path / "work" / "pids.txt")


# --- 3. bounded output capture ----------------------------------------------

def test_print_flood_is_truncated(tmp_path):
    result = run_student(tmp_path, """
        line = "y" * 1023
        for _ in range(20 * 1024):   # 20 MiB through print()
            print(line)
    """)
    assert len(result.stdout.encode()) < MIB + 200
    assert "output truncated" in result.stdout


def test_raw_output_flood_neither_hangs_nor_grows(tmp_path):
    start = time.monotonic()
    result = run_student(tmp_path, """
        import os
        chunk = b"z" * 65536
        while True:                  # endless, straight into the pipes
            os.write(1, chunk)
            os.write(2, chunk)
    """, timeout=3)
    assert result.timed_out
    assert time.monotonic() - start < 15
    for stream in (result.stdout, result.stderr):
        assert len(stream.encode()) < MIB + 200
        assert "output truncated" in stream


# --- 4. network and signal isolation (sandbox.launch) -----------------------

def _landlock_abi():
    from sandbox import launch
    return launch._landlock_abi()


@pytest.fixture
def sandboxed(monkeypatch):
    if _landlock_abi() < 6:
        pytest.skip("needs Landlock ABI >= 6 (TCP rules + scoping)")
    monkeypatch.setenv("COMPUTOR_SANDBOX_ENABLE", "1")


@pytest.fixture
def local_servers():
    """A TCP listener and a UDP receiver on loopback, owned by the 'worker'."""
    import socket
    tcp = socket.create_server(("127.0.0.1", 0))
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(("127.0.0.1", 0))
    udp.settimeout(0.5)
    yield tcp.getsockname()[1], udp
    tcp.close()
    udp.close()


NET_PROBE = """
    import errno, socket
    def attempt(fn):
        try:
            fn()
            return "OK"
        except OSError as e:
            return errno.errorcode.get(e.errno, str(e.errno))
    def udp(addr):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(b"exfil", addr)
    udp_dns = attempt(lambda: udp(("1.1.1.1", 53)))
    udp_local = attempt(lambda: udp(("127.0.0.1", {udp_port})))
    tcp_local = attempt(lambda: socket.create_connection(("127.0.0.1", {tcp_port}), 2))
    tcp_remote = attempt(lambda: socket.create_connection(("1.1.1.1", 80), 2))
    raw = attempt(lambda: socket.socket(socket.AF_INET, socket.SOCK_RAW, 1))
    packet = attempt(lambda: socket.socket(17, socket.SOCK_RAW, 0))
    fastopen = attempt(lambda: socket.socket().sendto(
        b"x", 0x20000000, ("127.0.0.1", {tcp_port})))
    unix_ok = attempt(lambda: socket.socketpair())
"""
NET_VARS = ["udp_dns", "udp_local", "tcp_local", "tcp_remote", "raw", "packet",
            "fastopen", "unix_ok"]


def test_network_egress_is_blocked(tmp_path, sandboxed, local_servers):
    tcp_port, udp = local_servers
    code = NET_PROBE.format(tcp_port=tcp_port, udp_port=udp.getsockname()[1])
    result = run_student(tmp_path, code, NET_VARS)
    assert result.success, result.error_message
    ns = result.namespace
    for name in ("udp_dns", "udp_local", "tcp_local", "tcp_remote", "raw",
                 "packet", "fastopen"):
        assert ns[name] == "EACCES", (name, ns)
    assert ns["unix_ok"] == "OK"  # local IPC keeps working
    with pytest.raises(OSError):  # and nothing arrived at the receiver
        udp.recv(64)


def test_network_probe_control_without_sandbox(tmp_path, local_servers):
    """The oracle itself: unsandboxed, the same probe reaches the servers."""
    tcp_port, udp = local_servers
    code = NET_PROBE.format(tcp_port=tcp_port, udp_port=udp.getsockname()[1])
    result = run_student(tmp_path, code, NET_VARS)
    assert result.namespace["tcp_local"] == "OK"
    assert result.namespace["udp_local"] == "OK"
    assert udp.recv(64) == b"exfil"


def test_job_cannot_signal_outside_its_domain(tmp_path, sandboxed):
    import subprocess
    bystander = subprocess.Popen(["sleep", "60"])  # a worker-side process
    try:
        result = run_student(tmp_path, f"""
            import os, signal
            def attempt(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                    return "KILLED"
                except OSError as e:
                    return e.errno
            parent = attempt(os.getppid())
            bystander = attempt({bystander.pid})
            worker = attempt({os.getpid()})
        """, ["parent", "bystander", "worker"])
        assert result.success, result.error_message
        assert result.namespace == {"parent": 1, "bystander": 1, "worker": 1}
        assert bystander.poll() is None
    finally:
        bystander.kill()
        bystander.wait()


ESCAPE_SESSION = textwrap.dedent("""
    import os, subprocess, time
    escaped = subprocess.Popen(["setsid", "sleep", "1000"])
    r, w = os.pipe()
    if os.fork() == 0:
        os.setsid()                       # leave the job's process group
        if os.fork() == 0:
            os.write(w, str(os.getpid()).encode())
            time.sleep(1000)
        os._exit(0)
    grandchild = int(os.read(r, 32))
    with open("pids.txt", "w") as f:
        f.write(f"{escaped.pid} {grandchild}")
""")


@pytest.mark.parametrize("finish", ["timeout", "exit"])
def test_setsid_escapees_are_killed(tmp_path, sandboxed, finish):
    tail = "time.sleep(1000)\n" if finish == "timeout" else "done = True\n"
    result = run_student(tmp_path, ESCAPE_SESSION + tail, timeout=4)
    assert result.timed_out == (finish == "timeout")
    assert_all_dead(tmp_path / "work" / "pids.txt")


def test_numpy_and_matplotlib_work_in_sandbox(tmp_path, sandboxed):
    test_numpy_and_matplotlib_work_under_default_limits(tmp_path)


def test_old_landlock_fails_closed(monkeypatch):
    from sandbox import launch
    monkeypatch.setattr(launch, "_landlock_abi", lambda: 3)
    with pytest.raises(OSError, match="cannot restrict TCP"):
        launch.apply_landlock([], [], allow_net=False)


# --- 5. compile step under the sandbox --------------------------------------

def _c_executor(tmp_path, source):
    import shutil
    if not shutil.which("gcc"):
        pytest.skip("gcc not installed")
    from testers.executors.c import CExecutor
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    (work / "main.c").write_text(textwrap.dedent(source))
    return CExecutor(working_dir=str(work))


def test_sandboxed_c_compile_and_run(tmp_path, sandboxed):
    executor = _c_executor(tmp_path, """
        #include <stdio.h>
        int main(void) { int x; if (scanf("%d", &x) != 1) return 3;
                         printf("got %d\\n", 2 * x); return 0; }
    """)
    assert executor.compile(["main.c"]).success
    result = executor.run(stdin="21")
    assert result.return_code == 0, result.stderr
    assert result.stdout == "got 42\n"


def test_compiler_cannot_include_worker_files(tmp_path, sandboxed):
    secret = tmp_path / "reference_solution.c"
    secret.write_text("TOPSECRET_REFERENCE_LINE\n")
    executor = _c_executor(tmp_path, f"""
        #include "{secret}"
        int main(void) {{ return 0; }}
    """)
    compiled = executor.compile(["main.c"])
    assert not compiled.success
    assert "TOPSECRET" not in compiled.stderr + compiled.stdout
    assert "Permission denied" in compiled.stderr


# --- 6. student-controlled result/report files ------------------------------

# The job finds its result file next to the wrapper (sys.argv[0]), replaces
# it, and exits before the wrapper writes the real result.
REPLACE_RESULT = """
    import glob, os, sys
    result = glob.glob(os.path.join(os.path.dirname(sys.argv[0]), "*.json"))[0]
    os.unlink(result)
    {action}
    os._exit(0)
"""


@pytest.fixture
def no_hang():
    import signal

    def _fail(*_):
        raise AssertionError("harness hung reading a student file")
    old = signal.signal(signal.SIGALRM, _fail)
    signal.alarm(30)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, old)


def test_symlinked_result_does_not_leak_worker_file(tmp_path, no_hang):
    secret = tmp_path / "worker_only.json"
    secret.write_text('{"status": "COMPLETED", "variables": {"leak": "TOPSECRET"}}')
    result = run_student(tmp_path, REPLACE_RESULT.format(
        action=f"os.symlink({str(secret)!r}, result)"))
    assert not result.success
    assert "leak" not in result.namespace
    assert result.error_type == "UnsafeFileError"
    assert "symlink" in result.error_message


def test_huge_result_file_is_refused(tmp_path, monkeypatch, no_hang):
    monkeypatch.setenv("COMPUTOR_JOB_MAX_FILE_SIZE", "0")  # no RLIMIT_FSIZE
    result = run_student(tmp_path, REPLACE_RESULT.format(
        action="open(result, 'wb').truncate(1 << 30)"))  # 1 GiB, sparse
    assert not result.success
    assert result.error_type == "UnsafeFileError"
    assert "too large" in result.error_message


def test_fifo_result_file_does_not_hang(tmp_path, no_hang):
    start = time.monotonic()
    result = run_student(tmp_path, REPLACE_RESULT.format(
        action="os.mkfifo(result)"))
    assert time.monotonic() - start < 20
    assert not result.success
    assert result.error_type == "UnsafeFileError"
    assert "not a regular file" in result.error_message


def test_symlinked_student_source_is_not_read(tmp_path):
    from ctexec.safe_io import UnsafeFileError, read_untrusted_text
    secret = tmp_path / "reference.c"
    secret.write_text("TOPSECRET")
    link = tmp_path / "main.c"
    link.symlink_to(secret)
    with pytest.raises(UnsafeFileError, match="symlink"):
        read_untrusted_text(str(link))


# --- 7. no pid-reuse window before the group kill ---------------------------

def _record_killpg(monkeypatch):
    """Record, at each killpg, whether the pgid's leader still holds its pid."""
    seen = []
    real_killpg = os.killpg

    def killpg(pgid, sig):
        seen.append(os.path.exists(f"/proc/{pgid}"))
        return real_killpg(pgid, sig)
    monkeypatch.setattr(os, "killpg", killpg)
    return seen


@pytest.mark.parametrize("script,timeout", [("exit 0", 10), ("sleep 30", 1)])
def test_leader_unreaped_until_group_killed(monkeypatch, script, timeout):
    from ctexec.process import run_bounded
    seen = _record_killpg(monkeypatch)
    result = run_bounded(["sh", "-c", script], timeout=timeout)
    assert result.timed_out == (timeout == 1)
    assert seen and all(seen)
