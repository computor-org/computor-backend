"""Requests to the worker host's computor-coder-hostops units.

The coder worker reaches Docker only through a proxy that refuses container
create and exec (see ops/docker/coder-worker-socket-proxy). The two operations
that needed them run on the host instead, as root, from a spool directory the
worker shares with the host:

* ``chown-volume``: give a workspace volume's files back to uid 1000;
* ``registry-gc``: drop superseded version tags from the local registry and
  garbage-collect its blobs.

Protocol (the host side is ops/coder/hostops/computor-coder-hostops.sh):

1. The worker writes ``staging/<id>`` and renames it to ``requests/<id>.req``.
   Writing in ``staging`` first keeps half-written files out of ``requests``,
   whose non-emptiness is what triggers the host's path unit.
2. The host claims the request, runs it and renames its answer into
   ``results/<id>``.
3. The worker waits for that file, reads and removes it.

Both sides speak ``key=value`` lines. A request the host never claims is
withdrawn when the worker stops waiting, so a stalled host does not run it
later behind the worker's back.

``registry.lock`` (root-owned) serialises registry pushes against garbage
collection: the worker holds a shared lock while it pushes, the host an
exclusive one while it collects. A collection racing a push can delete blobs
whose manifest has not arrived yet.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
import time
import uuid
from typing import Callable, Dict, Iterator, List, Optional, Tuple

from .worker_settings import get_worker_settings

POLL_SECONDS = 0.5


def hostops_dir() -> str:
    return get_worker_settings().hostops_dir


def available() -> bool:
    base = hostops_dir()
    return all(os.path.isdir(os.path.join(base, d)) for d in ("staging", "requests", "results"))


def parse_result(text: str) -> Dict[str, object]:
    """Parse the host's answer; ``removed`` and ``volume`` may repeat, every
    other key once."""
    values: Dict[str, object] = {"removed": [], "volume": []}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in ("removed", "volume"):
            values[key].append(value)  # type: ignore[union-attr]
        else:
            values[key] = value
    return values


def submit(
    action: str,
    fields: List[Tuple[str, str]],
    timeout: float,
    heartbeat: Optional[Callable[[], None]] = None,
) -> Dict[str, object]:
    """Hand one request to the host and wait for its answer.

    Never raises: returns ``{"status": "ok"|"error", "message": ...}`` plus
    whatever the host reported.
    """
    base = hostops_dir()
    if not available():
        return {
            "status": "error",
            "message": (
                f"host operations are not set up ({base} is missing staging/, "
                "requests/ or results/; install ops/coder/hostops on the worker host)"
            ),
        }
    request_id = uuid.uuid4().hex
    staged = os.path.join(base, "staging", request_id)
    queued = os.path.join(base, "requests", f"{request_id}.req")
    result_path = os.path.join(base, "results", request_id)
    body = "".join(f"{k}={v}\n" for k, v in [("action", action), *fields])
    try:
        with open(staged, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.rename(staged, queued)
    except OSError as e:
        return {"status": "error", "message": f"could not queue host request: {e}"}

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if heartbeat is not None:
            heartbeat()
        try:
            with open(result_path, encoding="utf-8") as fh:
                text = fh.read(65536)
        except FileNotFoundError:
            time.sleep(POLL_SECONDS)
            continue
        with contextlib.suppress(OSError):
            os.unlink(result_path)
        result = parse_result(text)
        result.setdefault("status", "error")
        result.setdefault("message", "")
        return result

    try:
        os.unlink(queued)
        withdrawn = " (request withdrawn)"
    except FileNotFoundError:
        withdrawn = " (the host claimed it and may still finish it)"
    return {
        "status": "error",
        "message": (
            f"host did not answer '{action}' within {int(timeout)}s{withdrawn}; "
            "is computor-coder-hostops.path active on the worker host?"
        ),
    }


@contextlib.contextmanager
def registry_push_lock(heartbeat: Optional[Callable[[], None]] = None) -> Iterator[None]:
    """Shared lock against the host's registry garbage collection.

    Waits (heartbeating) while a collection runs. Without host operations
    there is no host-side collection to race, so the lock is skipped.
    """
    path = os.path.join(hostops_dir(), "registry.lock")
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        yield
        return
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if heartbeat is not None:
                    heartbeat()
                time.sleep(1)
        yield
    finally:
        os.close(fd)
