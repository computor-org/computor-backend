"""Templates being deployed right now, as reported to ordinary users.

Nothing is pushed to Coder automatically, so between an admin choosing a
template and a user being able to pick it there is a build that Coder knows
nothing about. `GET /coder/templates` therefore has to say what is coming, and
say it under exactly the scoping rules that decide what the user may pick —
otherwise it advertises templates that will never be theirs.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computor_backend.api.coder import list_templates
from computor_backend.coder import templates_fs
from computor_backend.coder.config import CoderSettings
from computor_backend.coder.schemas import CoderTemplate
from computor_backend.permissions.principal import Principal
from computor_types.tasks import TaskInfo, TaskStatus


@pytest.fixture(autouse=True)
def no_deployment_fallback(monkeypatch):
    """Templates resolve from the fixture root only — see the catalog tests:
    resolve_templates_root() otherwise falls back to a real directory on the
    developer's own machine."""
    monkeypatch.delenv("SYSTEM_DEPLOYMENT_PATH", raising=False)


def _admin() -> Principal:
    return Principal(user_id="admin", roles=["_admin"])


def _workspace_user() -> Principal:
    """Holds workspace:templates, so: globally enabled templates, no courses."""
    principal = Principal(user_id="u1", roles=["_workspace_user"])
    principal.claims.general["workspace"] = {"templates", "provision_self"}
    return principal


def _settings(templates_dir: str = "/nonexistent") -> CoderSettings:
    return CoderSettings(
        admin_email="admin@example.com", admin_password="x", templates_dir=templates_dir,
    )


def _client(templates) -> MagicMock:
    client = MagicMock()
    client.list_templates = AsyncMock(return_value=templates)
    return client


def _task(
    templates,
    status: TaskStatus = TaskStatus.STARTED,
    task_name: str = "push_coder_templates",
) -> TaskInfo:
    return TaskInfo(
        task_id="wf-1",
        task_name=task_name,
        status=status,
        created_at="2026-07-30T10:00:00Z",
        workflow_id="wf-1",
        progress={"phase": "building", "templates": templates},
    )


def _entry(key: str, name: str, **changes) -> dict:
    entry = {
        "key": key,
        "name": name,
        "display_name": None,
        "status": "running",
        "phase": "building",
        "error": None,
    }
    entry.update(changes)
    return entry


class _NoCache:
    """Redis with nothing in it; the write is accepted and dropped.

    The real cache is keyed globally, so tests that shared it would leak one
    run's progress into the next.
    """

    async def get(self, key):
        return None

    async def set(self, key, value, ex=None):
        # Still exercise the encode path — a payload that cannot be serialised
        # would otherwise only fail in production.
        json.dumps(json.loads(value))


async def _run(principal, client, db, tasks, settings=None):
    """Call the endpoint with the Temporal feed and the cache stubbed out.

    Awaited inside the patch, not returned from it — a coroutine handed back
    to the caller would run with the real Temporal client.
    """
    with patch("computor_backend.api.coder._recent_coder_tasks", AsyncMock(return_value=tasks)), \
         patch("computor_backend.api.coder.get_redis_client", AsyncMock(return_value=_NoCache())):
        return await list_templates(principal, settings or _settings(), client, db)


@pytest.fixture
def templates_root(tmp_path):
    """One template on disk, with the metadata its card will need."""
    root = tmp_path / "templates"
    tpl = root / "matlab"
    tpl.mkdir(parents=True)
    (tpl / "template.json").write_text(json.dumps({
        "coder_template_name": "matlab-workspace",
        "display_name": "MATLAB",
        "description": "MATLAB desktop",
        "icon": "/icon/matlab.svg",
    }))
    (tpl / templates_fs.MANAGED_MARKER).write_text("")
    return str(root)


@pytest.mark.asyncio
async def test_a_template_being_built_is_reported_with_its_stage(templates_root):
    """The case the whole thing exists for: Coder has nothing to list yet."""
    task = _task([_entry("matlab", "matlab-workspace")])

    response = await _run(
        _admin(), _client([]), MagicMock(), [task], _settings(templates_root),
    )

    assert response.templates == []
    assert len(response.preparing) == 1
    matlab = response.preparing[0]
    assert matlab.name == "matlab-workspace"
    assert (matlab.status, matlab.phase) == ("running", "building")
    # Not in Coder yet — the card is not selectable, and says why.
    assert matlab.deployed is False
    # Progress carries no description or icon; the manifest on disk does.
    assert matlab.display_name == "MATLAB"
    assert matlab.description == "MATLAB desktop"
    assert matlab.icon == "/icon/matlab.svg"


@pytest.mark.asyncio
async def test_a_finished_template_drops_out_of_preparing():
    """Once it succeeds Coder has it, so it belongs in `templates` — once."""
    live = CoderTemplate(id="t1", name="vscode-workspace", display_name="VS Code")
    task = _task([
        _entry("vscode", "vscode-workspace", status="succeeded", phase="complete"),
        _entry("matlab", "matlab-workspace", status="pending", phase="queued"),
    ])

    response = await _run(_admin(), _client([live]), MagicMock(), [task])

    assert [t.name for t in response.templates] == ["vscode-workspace"]
    assert [p.name for p in response.preparing] == ["matlab-workspace"]


@pytest.mark.asyncio
async def test_a_rebuild_of_a_live_template_is_marked_deployed():
    """A re-push leaves the current version usable, so the card stays live."""
    live = CoderTemplate(id="t1", name="vscode-workspace", display_name="VS Code")
    task = _task([_entry("vscode", "vscode-workspace", phase="pushing")])

    response = await _run(_admin(), _client([live]), MagicMock(), [task])

    assert [t.name for t in response.templates] == ["vscode-workspace"]
    assert response.preparing[0].deployed is True


@pytest.mark.asyncio
async def test_a_finished_run_reports_only_what_failed():
    """A run that is over leaves everything it never reached at 'pending'.

    Those entries are stale, but the failure is not: without it a card that
    read "Building image" would simply vanish mid-wait.
    """
    task = _task(
        [
            _entry("matlab", "matlab-workspace", status="failed", phase="building"),
            _entry("bash", "bash-workspace", status="pending", phase="queued"),
        ],
        status=TaskStatus.FAILED,
    )

    response = await _run(_admin(), _client([]), MagicMock(), [task])

    assert [(p.name, p.status) for p in response.preparing] == [
        ("matlab-workspace", "failed"),
    ]


@pytest.mark.asyncio
async def test_a_rollout_is_not_reported_as_a_template_preparation():
    """A rollout updates existing workspaces; it changes nothing a user picks."""
    task = _task(
        [_entry("vscode", "vscode-workspace", phase="rolling_out")],
        task_name="rollout_workspaces",
    )

    response = await _run(_admin(), _client([]), MagicMock(), [task])

    assert response.preparing == []


@pytest.mark.asyncio
async def test_preparing_is_scoped_like_the_templates_beside_it():
    """A disabled template is not offered, so it is not promised either."""
    task = _task([
        _entry("matlab", "matlab-workspace"),
        _entry("bash", "bash-workspace"),
    ])

    with patch(
        "computor_backend.api.coder.get_disabled_template_names",
        return_value={"matlab-workspace"},
    ):
        response = await _run(_workspace_user(), _client([]), MagicMock(), [task])

    assert [p.name for p in response.preparing] == ["bash-workspace"]


@pytest.mark.asyncio
async def test_course_members_only_see_their_own_courses_builds():
    """Course-scoped users get course templates — including the pending one."""
    task = _task([
        _entry("matlab", "matlab-workspace"),
        _entry("bash", "bash-workspace"),
    ])

    member = Principal(user_id="student", roles=[])
    with patch(
        "computor_backend.api.coder.get_member_course_template_names",
        return_value={"bash-workspace"},
    ), patch(
        "computor_backend.api.coder.get_disabled_template_names", return_value=set(),
    ):
        response = await _run(member, _client([]), MagicMock(), [task])

    assert [p.name for p in response.preparing] == ["bash-workspace"]


@pytest.mark.asyncio
async def test_nothing_running_reports_nothing():
    live = CoderTemplate(id="t1", name="vscode-workspace")
    response = await _run(_admin(), _client([live]), MagicMock(), [])

    assert [t.name for t in response.templates] == ["vscode-workspace"]
    assert response.preparing == []


@pytest.mark.asyncio
async def test_an_unreachable_workflow_service_does_not_break_the_listing():
    """The stage bar is decoration; the list of templates is the endpoint."""
    live = CoderTemplate(id="t1", name="vscode-workspace")
    client = _client([live])

    with patch(
        "computor_backend.api.coder._recent_coder_tasks",
        AsyncMock(side_effect=RuntimeError("temporal is down")),
    ), patch(
        "computor_backend.api.coder.get_redis_client", AsyncMock(return_value=_NoCache()),
    ):
        response = await list_templates(_admin(), _settings(), client, MagicMock())

    assert [t.name for t in response.templates] == ["vscode-workspace"]
    assert response.preparing == []
