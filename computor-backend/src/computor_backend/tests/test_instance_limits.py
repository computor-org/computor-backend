"""Deployment-wide admission limits (#351).

Covers the three things the issue actually asks for: that a plain user is
refused with a message they can act on, that admins and maintainers are not,
and that the pre-existing per-template licence quota still binds everyone —
the two limits are deliberately different and must not collapse into one.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from computor_backend.business_logic import instance_limits
from computor_backend.business_logic.course_workspaces import (
    enforce_workspace_admission,
)
from computor_backend.business_logic.instance_limits import (
    STAFF_BYPASS_ROLES,
    active_workspace_owners,
    enforce_login_cap,
    enforce_workspace_user_cap,
    principal_is_staff,
)
from computor_backend.coder.schemas import CoderWorkspace, WorkspaceBuildStatus
from computor_backend.exceptions import ConflictException, ForbiddenException
from computor_backend.model.instance import InstanceSettings
from computor_backend.model.workspace import WorkspaceTemplateSettings
from computor_backend.permissions.principal import Principal


def _workspace(id_: str, owner: str, template: str = "vscode-workspace",
               transition="start",
               status=WorkspaceBuildStatus.SUCCEEDED) -> CoderWorkspace:
    return CoderWorkspace(
        id=id_, name=id_, owner_id=owner, owner_name=owner, template_id="t1",
        template_name=template, latest_build_transition=transition,
        latest_build_status=status,
    )


def _db(instance_row=None, template_row=None, roles=()):
    """Mock Session serving the instance row, a template row, and user roles.

    The three queries are told apart by the model they select, which is how the
    production code distinguishes them too.
    """
    db = MagicMock()

    def query(*entities):
        result = MagicMock()
        entity = entities[0]
        if entity is InstanceSettings:
            result.first.return_value = instance_row
        elif entity is WorkspaceTemplateSettings:
            result.filter.return_value.first.return_value = template_row
        else:  # UserRole.role_id
            result.filter.return_value.all.return_value = [(r,) for r in roles]
        return result

    db.query.side_effect = query
    return db


# --- who bypasses ------------------------------------------------------------


def test_admins_and_managers_bypass_but_workspace_users_do_not():
    assert principal_is_staff(Principal(user_id="u", roles=["_admin"]))
    assert principal_is_staff(Principal(user_id="u", roles=["_workspace_maintainer"]))
    assert principal_is_staff(Principal(user_id="u", roles=["_organization_manager"]))
    # is_service: the testing workers and the tutor agent must never be shed.
    assert principal_is_staff(Principal(user_id="u", is_service=True))
    # _workspace_user is builtin but held by ordinary students — bypassing on
    # the "_" prefix instead of this list would exempt everybody.
    assert "_workspace_user" not in STAFF_BYPASS_ROLES
    assert not principal_is_staff(Principal(user_id="u", roles=["_workspace_user"]))
    assert not principal_is_staff(Principal(user_id="u", roles=[]))


# --- workspace-user cap ------------------------------------------------------


def test_workspace_cap_counts_users_not_workspaces():
    # Three workspaces, two owners: one seat each, so a cap of 2 is reached.
    workspaces = [
        _workspace("a", "ualice"),
        _workspace("b", "ualice", template="matlab-ui-workspace"),
        _workspace("c", "ubob"),
    ]
    assert active_workspace_owners(workspaces) == {"ualice", "ubob"}

    db = _db(instance_row=InstanceSettings(max_workspace_users=2))
    with pytest.raises(ConflictException) as excinfo:
        enforce_workspace_user_cap(db, workspaces, "ucarol", is_staff=False)
    assert "2 concurrent workspace user(s)" in excinfo.value.detail

    # Alice already holds a seat, so her second workspace is not a new user.
    enforce_workspace_user_cap(db, workspaces, "ualice", is_staff=False)


def test_workspace_cap_refusal_points_at_the_local_install(monkeypatch):
    monkeypatch.setenv("EXTENSION_PUBLIC_DOWNLOAD_URL", "https://example.org/computor.vsix")
    db = _db(instance_row=InstanceSettings(max_workspace_users=1))
    with pytest.raises(ConflictException) as excinfo:
        enforce_workspace_user_cap(db, [_workspace("a", "ualice")], "ubob", is_staff=False)
    detail = excinfo.value.detail
    assert "https://example.org/computor.vsix" in detail
    assert "your own VS Code" in detail

    # Without the URL configured the advice survives; only the link goes.
    monkeypatch.delenv("EXTENSION_PUBLIC_DOWNLOAD_URL")
    with pytest.raises(ConflictException) as excinfo:
        enforce_workspace_user_cap(db, [_workspace("a", "ualice")], "ubob", is_staff=False)
    assert "your own VS Code" in excinfo.value.detail
    assert "http" not in excinfo.value.detail


def test_workspace_cap_lets_staff_through_and_ignores_no_limit():
    db = _db(instance_row=InstanceSettings(max_workspace_users=1))
    enforce_workspace_user_cap(db, [_workspace("a", "ualice")], "ubob", is_staff=True)

    unlimited = _db(instance_row=InstanceSettings(max_workspace_users=None))
    enforce_workspace_user_cap(unlimited, [_workspace("a", "ualice")], "ubob", is_staff=False)

    # No row at all (fresh deployment) behaves exactly like no limit.
    enforce_workspace_user_cap(_db(), [_workspace("a", "ualice")], "ubob", is_staff=False)


def test_workspace_cap_excludes_the_workspace_being_restarted():
    # Starting your own stopped workspace back up must not be blocked by its
    # own build still reading "start".
    db = _db(instance_row=InstanceSettings(max_workspace_users=1))
    enforce_workspace_user_cap(
        db, [_workspace("a", "ualice")], "ubob", is_staff=False, exclude_workspace_id="a",
    )


# --- both limits together ----------------------------------------------------


@pytest.mark.asyncio
async def test_template_quota_still_binds_admins():
    """Regression: the licence cap is the one limit staff do NOT escape."""
    client = MagicMock()
    client.list_all_workspaces = AsyncMock(return_value=[
        _workspace("a", "ualice", template="matlab-ui-workspace"),
    ])
    db = _db(
        template_row=WorkspaceTemplateSettings(
            template_name="matlab-ui-workspace", max_running_workspaces=1,
        ),
    )
    with pytest.raises(ConflictException) as excinfo:
        await enforce_workspace_admission(
            db, client, "matlab-ui-workspace",
            owner_username="uadmin", is_staff=True,
        )
    assert "matlab-ui-workspace" in excinfo.value.detail


@pytest.mark.asyncio
async def test_admission_skips_coder_when_nothing_is_configured():
    client = MagicMock()
    client.list_all_workspaces = AsyncMock(return_value=[])
    await enforce_workspace_admission(
        _db(), client, "vscode-workspace", owner_username="ualice", is_staff=False,
    )
    client.list_all_workspaces.assert_not_awaited()


@pytest.mark.asyncio
async def test_admission_reads_the_fleet_once_for_both_limits():
    client = MagicMock()
    client.list_all_workspaces = AsyncMock(return_value=[_workspace("a", "ualice")])
    db = _db(
        instance_row=InstanceSettings(max_workspace_users=5),
        template_row=WorkspaceTemplateSettings(
            template_name="vscode-workspace", max_running_workspaces=5,
        ),
    )
    await enforce_workspace_admission(
        db, client, "vscode-workspace", owner_username="ubob", is_staff=False,
    )
    assert client.list_all_workspaces.await_count == 1


# --- concurrent-login cap ----------------------------------------------------


@pytest.mark.asyncio
async def test_login_cap_counts_users_not_sessions(monkeypatch):
    """Two tabs are one seat: the seat index is keyed by user id."""
    seats = {}

    async def touch(user_id, idle_seconds):
        seats[str(user_id)] = idle_seconds

    async def count(idle_seconds):
        return len(seats)

    async def holds(user_id, idle_seconds):
        return str(user_id) in seats

    monkeypatch.setattr(instance_limits, "touch_login_seat", touch)
    monkeypatch.setattr(instance_limits, "count_login_seats", count)
    monkeypatch.setattr(instance_limits, "holds_login_seat", holds)

    db = _db(instance_row=InstanceSettings(max_concurrent_logins=1, login_idle_minutes=30))

    await enforce_login_cap(db, "alice")
    await instance_limits.touch_login_seat("alice", 1800)
    # Alice signing in again from a second device is not a second user.
    await enforce_login_cap(db, "alice")
    assert len(seats) == 1

    with pytest.raises(ForbiddenException):
        await enforce_login_cap(db, "bob")


@pytest.mark.asyncio
async def test_login_cap_lets_staff_through(monkeypatch):
    monkeypatch.setattr(instance_limits, "count_login_seats", AsyncMock(return_value=99))
    monkeypatch.setattr(instance_limits, "holds_login_seat", AsyncMock(return_value=False))

    full = InstanceSettings(max_concurrent_logins=1, login_idle_minutes=30)
    with pytest.raises(ForbiddenException):
        await enforce_login_cap(_db(instance_row=full), "student")
    await enforce_login_cap(_db(instance_row=full, roles=["_admin"]), "admin")
    await enforce_login_cap(
        _db(instance_row=full, roles=["_workspace_maintainer"]), "maintainer"
    )


@pytest.mark.asyncio
async def test_login_cap_refusal_is_actionable(monkeypatch):
    monkeypatch.setenv("EXTENSION_PUBLIC_DOWNLOAD_URL", "https://example.org/computor.vsix")
    monkeypatch.setattr(instance_limits, "count_login_seats", AsyncMock(return_value=20))
    monkeypatch.setattr(instance_limits, "holds_login_seat", AsyncMock(return_value=False))

    db = _db(instance_row=InstanceSettings(max_concurrent_logins=20, login_idle_minutes=30))
    with pytest.raises(ForbiddenException) as excinfo:
        await enforce_login_cap(db, "student")
    detail = excinfo.value.detail
    assert "20 concurrent user(s)" in detail
    assert "20 currently signed in" in detail
    assert "https://example.org/computor.vsix" in detail


@pytest.mark.asyncio
async def test_login_cap_is_off_without_a_row_or_a_limit(monkeypatch):
    # Would refuse everyone if the guard were reached at all.
    monkeypatch.setattr(instance_limits, "count_login_seats", AsyncMock(return_value=10**6))
    monkeypatch.setattr(instance_limits, "holds_login_seat", AsyncMock(return_value=False))

    await enforce_login_cap(_db(), "student")
    await enforce_login_cap(
        _db(instance_row=InstanceSettings(max_concurrent_logins=None, login_idle_minutes=30)),
        "student",
    )
