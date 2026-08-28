"""What this process is and when it started (#350).

Facts an operator asks for and the API could not answer: when the server last
restarted, and which code it is running. Neither changes while the process
lives, so both are resolved once and cached.

The commit/branch half moved here from ``api/update.py``, which needed it to
compare the running version against the deployment repo's tip. Two endpoints now
report the same identity, and there is one definition of it.
"""
from datetime import datetime, timezone
from typing import Optional, Tuple

from computor_backend.config import get_settings

# Set by the FastAPI lifespan, so this is when the app came up rather than when
# some module happened to be imported.
_started_at: Optional[datetime] = None

# Resolved once per process: the running commit/branch never change while the
# process lives (env is baked at image build; dev reads the working tree).
_running_version: Optional[Tuple[str, str]] = None


def mark_started() -> None:
    """Record the process start. Called once, from the app's lifespan."""
    global _started_at
    if _started_at is None:
        _started_at = datetime.now(timezone.utc)


def started_at() -> datetime:
    """When this process came up.

    Falls back to *now* if the lifespan never ran — a test client or a script
    importing the app. A wrong-by-milliseconds answer beats a None every caller
    has to branch on.
    """
    if _started_at is None:
        mark_started()
    assert _started_at is not None
    return _started_at


def uptime_seconds() -> int:
    return int((datetime.now(timezone.utc) - started_at()).total_seconds())


def running_version() -> Tuple[str, str]:
    """(commit, branch) of the running code: baked env, else git discovery."""
    global _running_version
    if _running_version is not None:
        return _running_version

    settings = get_settings().update
    if settings.git_commit:
        _running_version = (settings.git_commit, settings.git_branch or "unknown")
        return _running_version

    # Dev fallback: the API runs from a git working tree on the host.
    try:
        import git

        repo = git.Repo(__file__, search_parent_directories=True)
        commit = repo.head.commit.hexsha
        try:
            branch = repo.active_branch.name
        except TypeError:  # detached HEAD
            branch = "detached"
        _running_version = (commit, branch)
    except Exception:
        _running_version = ("unknown", "unknown")
    return _running_version
