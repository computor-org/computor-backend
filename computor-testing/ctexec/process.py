"""Run one untrusted job as a bounded, killable process tree (#237).

:func:`run_bounded` replaces ``subprocess.run`` for student code:

- The job starts in its own session/process group (``start_new_session``), and
  when it finishes or times out the whole group is SIGKILLed, so detached
  children and double-forked grandchildren cannot outlive the job. The group
  leader is left unreaped (``waitid(WNOWAIT)``) until the kill, so its pgid
  cannot be recycled in between. Descendants that ``setsid()`` out of the
  group are handled by the sandbox launcher, which scopes the job in its own
  Landlock domain and kills that domain on exit (sandbox/launch.py).
- stdout/stderr are read incrementally by two threads, each keeping at most
  ``max_output`` bytes and discarding the rest, so a flood can neither exhaust
  the harness's memory nor deadlock the child on a full pipe.
"""

import os
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Callable, List, Optional

DEFAULT_MAX_OUTPUT_BYTES = 1024 * 1024
MAX_OUTPUT_ENV = "COMPUTOR_JOB_MAX_OUTPUT_BYTES"
TRUNCATION_MARKER = "\n[... output truncated: {dropped} more bytes discarded ...]\n"

# After SIGTERM to the group leader (the sandbox launcher cleans up its whole
# domain on SIGTERM), wait this long before SIGKILLing the group.
TERM_GRACE_SECONDS = 1.0
# How long to keep draining pipes after the tree is dead.
DRAIN_GRACE_SECONDS = 2.0


def max_output_bytes() -> int:
    raw = os.environ.get(MAX_OUTPUT_ENV, "").strip()
    try:
        value = int(raw) if raw else DEFAULT_MAX_OUTPUT_BYTES
    except ValueError:
        value = DEFAULT_MAX_OUTPUT_BYTES
    return value if value > 0 else DEFAULT_MAX_OUTPUT_BYTES


def truncate_text(text: Optional[str], limit: Optional[int] = None) -> str:
    """Cap already-collected text (e.g. from a result file) to ``limit`` bytes."""
    if not text:
        return text or ""
    limit = limit or max_output_bytes()
    data = text.encode("utf-8", errors="replace")
    if len(data) <= limit:
        return text
    kept = data[:limit].decode("utf-8", errors="ignore")
    return kept + TRUNCATION_MARKER.format(dropped=len(data) - limit)


@dataclass
class BoundedResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    duration: float


class _Capture(threading.Thread):
    """Drain one pipe, keeping the first ``limit`` bytes."""

    def __init__(self, stream, limit: int):
        super().__init__(daemon=True)
        self._fd = stream.fileno()
        self._stream = stream
        self._limit = limit
        self._chunks: List[bytes] = []
        self._kept = 0
        self.dropped = 0

    def run(self) -> None:
        try:
            while True:
                data = os.read(self._fd, 65536)
                if not data:
                    break
                room = self._limit - self._kept
                if room > 0:
                    self._chunks.append(data[:room])
                    self._kept += min(room, len(data))
                self.dropped += max(0, len(data) - max(room, 0))
        except OSError:
            pass
        finally:
            self._stream.close()

    def text(self) -> str:
        out = b"".join(self._chunks).decode("utf-8", errors="replace")
        if self.dropped:
            out += TRUNCATION_MARKER.format(dropped=self.dropped)
        return out


def _feed(stream, data: bytes) -> None:
    try:
        stream.write(data)
    except (BrokenPipeError, OSError, ValueError):
        pass
    finally:
        try:
            stream.close()
        except (BrokenPipeError, OSError, ValueError):
            pass


def _kill_group(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_bounded(
    cmd: List[str],
    *,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    input: Optional[str] = None,
    timeout: Optional[float] = None,
    preexec_fn: Optional[Callable[[], None]] = None,
    max_output: Optional[int] = None,
) -> BoundedResult:
    """Run ``cmd`` as a job: bounded output, whole tree killed at the end."""
    limit = max_output or max_output_bytes()
    start = time.perf_counter()
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=preexec_fn,
        start_new_session=True,
    )
    pgid = proc.pid  # session leader == process-group leader
    readers = [_Capture(proc.stdout, limit), _Capture(proc.stderr, limit)]
    for reader in readers:
        reader.start()
    if input is not None:
        threading.Thread(
            target=_feed, args=(proc.stdin, input.encode("utf-8")), daemon=True
        ).start()

    # Wait for the leader to exit WITHOUT reaping it, so its pid (== pgid)
    # stays reserved until the group kill below.
    leader_exited = threading.Event()

    def _wait_leader() -> None:
        try:
            os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOWAIT)
        except ChildProcessError:
            pass
        leader_exited.set()

    threading.Thread(target=_wait_leader, daemon=True).start()

    timed_out = False
    try:
        if not leader_exited.wait(timeout):
            timed_out = True
            try:
                proc.send_signal(signal.SIGTERM)
            except ProcessLookupError:
                pass
            leader_exited.wait(TERM_GRACE_SECONDS)
    finally:
        # The job is over, one way or another: nothing of its tree survives.
        _kill_group(pgid)
        leader_exited.wait()
        proc.wait()

    for reader in readers:
        reader.join(DRAIN_GRACE_SECONDS)
    return BoundedResult(
        returncode=proc.returncode,
        stdout=readers[0].text(),
        stderr=readers[1].text(),
        timed_out=timed_out,
        duration=time.perf_counter() - start,
    )
