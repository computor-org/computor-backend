"""Read files a student job could have planted or replaced (#237).

Result JSON, submitted sources and other report inputs live in directories
the job can write, so the harness must not trust what it finds there:

- ``O_NOFOLLOW``: a symlink (to /proc/self/environ, the reference cache,
  another job's files) is refused rather than followed.
- ``O_NONBLOCK`` + ``fstat``: only regular files are read; a FIFO or device
  is refused instead of blocking the harness forever.
- A size cap, checked before and while reading, so a huge or growing file
  cannot exhaust the harness's memory.

Violations raise :class:`UnsafeFileError` (an ``OSError``), which callers
turn into a clean job/test failure.
"""

import os
import stat

MIB = 1024 * 1024
RESULT_LIMIT_ENV = "COMPUTOR_JOB_MAX_RESULT_BYTES"
REPORT_LIMIT_ENV = "COMPUTOR_JOB_MAX_REPORT_BYTES"
DEFAULT_RESULT_LIMIT = 64 * MIB   # extracted variables can be large arrays
DEFAULT_REPORT_LIMIT = 10 * MIB   # sources, documents, other report inputs


class UnsafeFileError(OSError):
    """A student-controlled file was refused (symlink, non-regular, too big)."""


def _limit(env_var: str, default: int) -> int:
    raw = os.environ.get(env_var, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return value if value > 0 else default


def result_limit() -> int:
    return _limit(RESULT_LIMIT_ENV, DEFAULT_RESULT_LIMIT)


def report_limit() -> int:
    return _limit(REPORT_LIMIT_ENV, DEFAULT_REPORT_LIMIT)


def read_untrusted_bytes(path, max_bytes=None) -> bytes:
    """Read a regular, non-symlink file of at most ``max_bytes`` bytes."""
    max_bytes = max_bytes or report_limit()
    flags = (os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY
             | getattr(os, "O_CLOEXEC", 0))
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        if os.path.islink(path):
            raise UnsafeFileError(f"refusing to follow symlink: {path}") from exc
        raise
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise UnsafeFileError(f"not a regular file: {path}")
        if st.st_size > max_bytes:
            raise UnsafeFileError(
                f"file too large ({st.st_size} > {max_bytes} bytes): {path}")
        chunks, total = [], 0
        while True:
            chunk = os.read(fd, min(1 * MIB, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise UnsafeFileError(
                    f"file grew beyond {max_bytes} bytes: {path}")
        return b"".join(chunks)
    finally:
        os.close(fd)


def read_untrusted_text(path, max_bytes=None, encoding="utf-8") -> str:
    """Text variant of :func:`read_untrusted_bytes` (undecodable -> U+FFFD)."""
    return read_untrusted_bytes(path, max_bytes).decode(encoding, errors="replace")
