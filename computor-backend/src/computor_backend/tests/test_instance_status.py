"""Runtime status of the running API (#350).

Covers the three answers the endpoint gives — when the process started, what it
is running, when that was built — and the one refusal, since it is admin-only.
The interesting cases are the ones where the honest answer is "I don't know":
a working tree with no baked build, and a BUILD_TIME nobody can parse.
"""

import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from computor_backend.business_logic import build_info
from computor_backend.exceptions import ForbiddenException
from computor_backend.permissions.principal import Principal


@pytest.fixture(autouse=True)
def _clean_process_state(monkeypatch):
    """Both facts are cached for the life of the process — clear them per test."""
    monkeypatch.setattr(build_info, "_running_version", None)
    monkeypatch.setattr(build_info, "_started_at", None)
    yield


def _settings(monkeypatch, **update_fields):
    """Stand in for get_settings(), which reads the real environment."""
    class _Update:
        git_commit = update_fields.get("git_commit", "")
        git_branch = update_fields.get("git_branch", "")
        build_time = update_fields.get("build_time", "")

    class _Settings:
        update = _Update()

    monkeypatch.setattr(build_info, "get_settings", lambda: _Settings())


# --- build identity --------------------------------------------------------

def test_baked_env_wins_over_git_discovery(monkeypatch):
    _settings(monkeypatch, git_commit="abc123", git_branch="release/2026.10")
    assert build_info.running_version() == ("abc123", "release/2026.10")


def test_a_baked_commit_without_a_branch_says_so(monkeypatch):
    # Half-baked provenance is possible (an image built with only one arg).
    # "unknown" is the honest branch, not an empty string the UI would render blank.
    _settings(monkeypatch, git_commit="abc123")
    assert build_info.running_version() == ("abc123", "unknown")


def test_unknown_rather_than_a_crash_when_there_is_no_git_either(monkeypatch):
    # An image built without the args, running from a tree that is not a repo —
    # the one case where there is genuinely nothing to report.
    _settings(monkeypatch)

    def _no_repo(*args, **kwargs):
        raise ValueError("not a git repository")

    monkeypatch.setitem(sys.modules, "git", SimpleNamespace(Repo=_no_repo))
    assert build_info.running_version() == ("unknown", "unknown")


def test_the_version_is_resolved_once(monkeypatch):
    _settings(monkeypatch, git_commit="abc123", git_branch="main")
    assert build_info.running_version() == ("abc123", "main")

    _settings(monkeypatch, git_commit="def456", git_branch="other")
    # The running code cannot change under a live process, so neither does this.
    assert build_info.running_version() == ("abc123", "main")


# --- build time ------------------------------------------------------------

def test_no_build_time_in_a_working_tree(monkeypatch):
    _settings(monkeypatch)
    assert build_info.build_time() is None


def test_build_time_is_read_as_utc(monkeypatch):
    _settings(monkeypatch, build_time="2026-08-26T21:40:00Z")
    assert build_info.build_time() == datetime(2026, 8, 26, 21, 40, tzinfo=timezone.utc)


def test_a_naive_build_time_is_taken_as_utc(monkeypatch):
    # The stamp is produced by `date -u`, so a missing zone means UTC, not local.
    _settings(monkeypatch, build_time="2026-08-26T21:40:00")
    assert build_info.build_time() == datetime(2026, 8, 26, 21, 40, tzinfo=timezone.utc)


def test_an_unparseable_build_time_is_dropped_not_guessed(monkeypatch):
    _settings(monkeypatch, build_time="last tuesday")
    assert build_info.build_time() is None


# --- uptime ----------------------------------------------------------------

def test_start_time_is_recorded_once_and_uptime_follows_it(monkeypatch):
    build_info.mark_started()
    first = build_info.started_at()

    build_info.mark_started()
    assert build_info.started_at() == first  # a second call does not restart the clock

    monkeypatch.setattr(build_info, "_started_at", first - timedelta(seconds=90))
    assert build_info.uptime_seconds() >= 90


def test_reading_the_start_time_before_the_lifespan_ran_does_not_fail():
    # A test client or a script that imports the app never runs the lifespan.
    assert build_info.started_at().tzinfo is not None
    assert build_info.uptime_seconds() >= 0


# --- the endpoint ----------------------------------------------------------

@pytest.mark.asyncio
async def test_status_reports_the_running_process(monkeypatch):
    from computor_backend.api.instance import get_instance_status

    _settings(monkeypatch, git_commit="abc123", git_branch="release/2026.10",
              build_time="2026-08-26T21:40:00Z")
    build_info.mark_started()

    status = await get_instance_status(Principal(user_id="u", roles=["_admin"]))

    assert (status.commit, status.branch) == ("abc123", "release/2026.10")
    assert status.build_time == datetime(2026, 8, 26, 21, 40, tzinfo=timezone.utc)
    assert status.started_at == build_info.started_at()
    assert status.uptime_seconds >= 0


@pytest.mark.asyncio
async def test_status_is_admin_only(monkeypatch):
    from computor_backend.api.instance import get_instance_status

    _settings(monkeypatch, git_commit="abc123")
    with pytest.raises(ForbiddenException):
        await get_instance_status(Principal(user_id="u", roles=["_user"]))
