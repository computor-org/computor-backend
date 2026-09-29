"""Read files a student job could have planted or replaced (#237).

Result JSON, submitted sources and other report inputs live in directories
the job can write, so the harness must not trust what it finds there:

- No symlinks anywhere below a trusted root: each component is opened with
  ``O_NOFOLLOW`` relative to its parent's fd, so a symlinked file or
  directory (to /proc/self/environ, the reference cache, another job's
  files) is refused rather than followed.
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


def _open_beneath(root, path, leaf_flags: int) -> int:
    """Open ``path`` beneath the trusted directory ``root``, following no
    symlink in any component below it.

    ``root`` itself is trusted (created or chosen by the harness) and opened
    normally. Every component after it is opened relative to its parent's fd
    with ``O_NOFOLLOW`` (directories additionally with ``O_DIRECTORY``), so a
    symlinked directory is refused just like a symlinked leaf — something
    ``O_NOFOLLOW`` alone does not do for intermediate components.
    """
    root = os.path.abspath(root)
    target = os.path.abspath(path)
    rel = os.path.relpath(target, root)
    parts = rel.split(os.sep)
    if rel == os.curdir or os.path.isabs(rel) or any(
            p in ("", os.curdir, os.pardir) for p in parts):
        raise UnsafeFileError(f"not beneath {root}: {path}")
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    dirfd = os.open(root, dir_flags)
    try:
        for index, part in enumerate(parts):
            last = index == len(parts) - 1
            flags = leaf_flags if last else dir_flags | os.O_NOFOLLOW
            try:
                fd = os.open(part, flags, dir_fd=dirfd)
            except OSError as exc:
                try:
                    link = stat.S_ISLNK(os.stat(
                        part, dir_fd=dirfd, follow_symlinks=False).st_mode)
                except OSError:
                    link = False
                if link:
                    raise UnsafeFileError(
                        f"refusing to follow symlink {part!r} in {path}") from exc
                raise
            if last:
                return fd
            os.close(dirfd)
            dirfd = fd
    finally:
        os.close(dirfd)
    raise AssertionError("unreachable")


def read_untrusted_bytes(path, max_bytes=None, root=None) -> bytes:
    """Read a regular, symlink-free file of at most ``max_bytes`` bytes.

    ``root`` is the trusted directory the file must lie beneath (the job's
    working or result dir); no component below it may be a symlink. Without
    ``root`` only the file's own parent is trusted, so only the leaf is
    checked — pass the job directory whenever the caller knows it.
    """
    max_bytes = max_bytes or report_limit()
    if root is None:
        root = os.path.dirname(os.path.abspath(path))
    flags = (os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY
             | getattr(os, "O_CLOEXEC", 0))
    fd = _open_beneath(root, path, flags)
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


def read_untrusted_text(path, max_bytes=None, encoding="utf-8",
                        root=None) -> str:
    """Text variant of :func:`read_untrusted_bytes` (undecodable -> U+FFFD)."""
    return read_untrusted_bytes(path, max_bytes, root).decode(
        encoding, errors="replace")
