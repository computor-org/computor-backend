"""Course-scoped workspaces: template governance, course-derived access,
lecturer bulk provisioning of (throwaway) student workspaces."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import computor_backend.business_logic.course_workspaces as cw
from computor_backend.coder.service import MintResult
from computor_backend.api.coder import (
    _check_workspace_access_or_course_member,
    list_templates,
    provision_workspace,
    update_template_settings,
)
from computor_backend.coder.exceptions import CoderTemplateNotFoundError
from computor_backend.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
    ServiceUnavailableException,
)
from computor_backend.model.course import Course, CourseMember
from computor_backend.model.workspace import (
    CourseWorkspaceSettings,
    CourseWorkspaceTemplate,
    WorkspaceTemplateSettings,
)
from computor_backend.permissions.principal import Claims, Principal
from computor_types.coder import CoderTemplate, WorkspaceTemplateSettingsUpdate
from computor_types.course_workspaces import (
    CourseWorkspaceSettingsUpdate,
    StudentWorkspaceProvisionRequest,
)


# --- principals ---------------------------------------------------------------


def _admin() -> Principal:
    return Principal(user_id="admin", roles=["_admin"])


def _maintainer() -> Principal:
    """Global workspace maintainer (workspace:manage claim, no course roles)."""
    return Principal(
        user_id="wm", claims=Claims(general={"workspace": {
            "manage", "templates", "provision", "list", "access", "start", "stop",
        }}),
    )


def _workspace_user() -> Principal:
    return Principal(
        user_id="wu", claims=Claims(general={"workspace": {
            "templates", "provision_self", "list", "access", "start", "stop",
        }}),
    )


def _course_principal(user_id: str, course_id: str, role: str) -> Principal:
    """A user whose only claims are a course membership (no workspace role)."""
    return Principal(
        user_id=user_id,
        claims=Claims(dependent={"course": {course_id: {role}}}),
    )


# --- fake DB ------------------------------------------------------------------


_UNSET = object()


def make_db(
    *,
    course=_UNSET,
    course_templates=(),
    disabled=(),
    settings_row=None,
    course_settings=_UNSET,
    members=(),
    member_first=_UNSET,
):
    """Routing Session mock: dispatches on the db.query(...) target.

    ``course_templates`` are CourseWorkspaceTemplate rows; ``disabled`` are
    template names with enabled=false; ``settings_row`` serves the
    per-template settings lookup; ``members`` serve .all(), ``member_first``
    the .first() lookup of the bulk-provision loop.
    """
    db = MagicMock()
    course_obj = MagicMock(spec=Course) if course is _UNSET else course
    state = {"course_settings": None if course_settings is _UNSET else course_settings}

    def add(obj):
        # Make an upserted settings row visible to follow-up reads.
        if isinstance(obj, CourseWorkspaceSettings):
            state["course_settings"] = obj

    def query(target):
        q = MagicMock()
        if target is CourseWorkspaceTemplate.template_name:
            q.filter.return_value.distinct.return_value.all.return_value = [
                (r.template_name,) for r in course_templates
            ]
        elif target is WorkspaceTemplateSettings.template_name:
            rows = [(n,) for n in disabled]
            q.filter.return_value.all.return_value = rows
            q.filter.return_value.filter.return_value.all.return_value = rows
        elif target is WorkspaceTemplateSettings:
            q.filter.return_value.first.return_value = settings_row
        elif target is CourseWorkspaceTemplate:
            # The real query orders by template_name; the fake mirrors that.
            q.filter.return_value.order_by.return_value.all.return_value = sorted(
                course_templates, key=lambda r: r.template_name
            )
        elif target is CourseWorkspaceSettings:
            q.filter.return_value.first = lambda: state["course_settings"]
        elif target is Course:
            q.filter.return_value.first.return_value = course_obj
            q.order_by.return_value.all.return_value = [course_obj] if course_obj else []
        elif target is CourseMember:
            q.filter.return_value.all.return_value = list(members)
            q.filter.return_value.first.return_value = (
                None if member_first is _UNSET else member_first
            )
        return q

    db.query.side_effect = query
    db.add.side_effect = add
    return db


def _tpl_row(course_id: str, name: str) -> CourseWorkspaceTemplate:
    return CourseWorkspaceTemplate(course_id=course_id, template_name=name)


def _coder_template(name: str) -> CoderTemplate:
    return CoderTemplate(id=name, name=name, display_name=name.title(), icon="/icon/x.svg")


# --- course-derived template set ---------------------------------------------


def test_member_templates_intersect_courses_and_drop_disabled():
    principal = _course_principal("s1", "c1", "_student")
    db = make_db(
        course_templates=[_tpl_row("c1", "vscode-workspace"), _tpl_row("c1", "bash-workspace")],
        disabled=["bash-workspace"],
    )
    assert cw.get_member_course_template_names(db, principal) == {"vscode-workspace"}


def test_member_templates_no_settings_row_counts_as_enabled():
    principal = _course_principal("s1", "c1", "_student")
    db = make_db(course_templates=[_tpl_row("c1", "vscode-workspace")])
    assert cw.get_member_course_template_names(db, principal) == {"vscode-workspace"}


def test_member_templates_without_membership_is_empty_and_skips_db():
    db = make_db()
    assert cw.get_member_course_template_names(db, Principal(user_id="x")) == set()
    db.query.assert_not_called()


# --- access fallback matrix ---------------------------------------------------


def test_fallback_grants_member_own_workspace_actions():
    principal = _course_principal("s1", "c1", "_student")
    db = make_db(course_templates=[_tpl_row("c1", "vscode-workspace")])
    for action in ("access", "list", "start", "stop", "templates"):
        _check_workspace_access_or_course_member(principal, action, db)
        _check_workspace_access_or_course_member(principal, action, db, username="s1")


def test_fallback_rejects_foreign_username():
    principal = _course_principal("s1", "c1", "_student")
    db = make_db(course_templates=[_tpl_row("c1", "vscode-workspace")])
    with pytest.raises(ForbiddenException):
        _check_workspace_access_or_course_member(principal, "start", db, username="other")


def test_fallback_never_covers_privileged_actions():
    principal = _course_principal("s1", "c1", "_student")
    db = make_db(course_templates=[_tpl_row("c1", "vscode-workspace")])
    for action in ("delete", "manage", "session", "provision"):
        with pytest.raises(ForbiddenException):
            _check_workspace_access_or_course_member(principal, action, db)


def test_fallback_denies_without_course_templates():
    principal = _course_principal("s1", "c1", "_student")
    with pytest.raises(ForbiddenException):
        _check_workspace_access_or_course_member(principal, "list", make_db())


def test_global_claim_holders_keep_foreign_access():
    # A maintainer may touch other users' workspaces; username is not checked.
    _check_workspace_access_or_course_member(_maintainer(), "start", make_db(), username="other")


# --- template listing ---------------------------------------------------------


def _list_client(names):
    client = MagicMock()
    client.list_templates = AsyncMock(return_value=[_coder_template(n) for n in names])
    return client


@pytest.mark.asyncio
async def test_list_templates_manager_sees_disabled_users_do_not():
    client = _list_client(["vscode-workspace", "bash-workspace"])
    db = make_db(disabled=["bash-workspace"])

    result = await list_templates(_maintainer(), MagicMock(), client, db)
    assert {t.name for t in result.templates} == {"vscode-workspace", "bash-workspace"}

    result = await list_templates(_workspace_user(), MagicMock(), client, db)
    assert {t.name for t in result.templates} == {"vscode-workspace"}


@pytest.mark.asyncio
async def test_list_templates_course_member_sees_allowed_intersection():
    client = _list_client(["vscode-workspace", "bash-workspace", "jupyter-workspace"])
    principal = _course_principal("s1", "c1", "_student")
    db = make_db(
        course_templates=[_tpl_row("c1", "vscode-workspace"), _tpl_row("c1", "jupyter-workspace")],
        disabled=["jupyter-workspace"],
    )
    result = await list_templates(principal, MagicMock(), client, db)
    assert {t.name for t in result.templates} == {"vscode-workspace"}


@pytest.mark.asyncio
async def test_list_templates_denies_without_claim_or_membership():
    with pytest.raises(ForbiddenException):
        await list_templates(Principal(user_id="x"), MagicMock(), _list_client([]), make_db())


# --- provisioning scoping -----------------------------------------------------


def _provision_settings():
    settings = MagicMock()
    settings.default_template = "vscode-workspace"
    return settings


@pytest.mark.asyncio
async def test_course_member_cannot_provision_outside_allowed_set():
    from computor_types.workspace_roles import WorkspaceProvisionRequest
    principal = _course_principal("s1", "c1", "_student")
    db = make_db(course_templates=[_tpl_row("c1", "vscode-workspace")])
    request = WorkspaceProvisionRequest(template="bash-workspace")
    with pytest.raises(ForbiddenException) as exc:
        await provision_workspace(
            request, principal, _provision_settings(), MagicMock(), db, MagicMock()
        )
    assert "not available for your courses" in str(exc.value)


@pytest.mark.asyncio
async def test_course_member_provision_forces_self_semantics_and_shared_home():
    from computor_types.workspace_roles import WorkspaceProvisionRequest
    principal = _course_principal("s1", "c1", "_student")
    db = make_db(course_templates=[_tpl_row("c1", "vscode-workspace")])
    client = MagicMock()
    # Passing the scoping + disabled gates proves course-derived provisioning
    # is allowed; the template-exists check then raises the typed 503.
    client.get_template_id = AsyncMock(side_effect=CoderTemplateNotFoundError("x"))
    request = WorkspaceProvisionRequest(
        template="vscode-workspace", workspace_name="custom", home_mode="scratch"
    )
    with pytest.raises(ServiceUnavailableException):
        await provision_workspace(
            request, principal, _provision_settings(), client, db, MagicMock()
        )
    assert request.workspace_name is None
    assert request.home_mode is None


@pytest.mark.asyncio
async def test_disabled_template_blocks_provision_self_but_not_admin():
    from computor_types.workspace_roles import WorkspaceProvisionRequest
    disabled_row = WorkspaceTemplateSettings(
        template_name="vscode-workspace", enabled=False,
    )
    db = make_db(settings_row=disabled_row)
    client = MagicMock()
    client.get_template_id = AsyncMock(side_effect=CoderTemplateNotFoundError("x"))

    with pytest.raises(ForbiddenException) as exc:
        await provision_workspace(
            WorkspaceProvisionRequest(template="vscode-workspace"),
            _workspace_user(), _provision_settings(), client, db, MagicMock(),
        )
    assert "currently disabled" in str(exc.value)

    # Admin passes the disabled gate (503 = it reached the template-exists check).
    with pytest.raises(ServiceUnavailableException):
        await provision_workspace(
            WorkspaceProvisionRequest(template="vscode-workspace"),
            _admin(), _provision_settings(), client, db, MagicMock(),
        )


# --- template settings enabled round-trip ------------------------------------


@pytest.mark.asyncio
async def test_settings_update_round_trips_enabled_flag():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    result = await update_template_settings(
        "vscode-workspace",
        WorkspaceTemplateSettingsUpdate(enabled=False),
        _admin(), MagicMock(), db,
    )
    assert result.enabled is False


# --- course workspace settings ------------------------------------------------


def _coder_settings(enabled=True):
    settings = MagicMock()
    settings.enabled = enabled
    return settings


@pytest.mark.asyncio
async def test_settings_put_requires_workspace_manage_not_course_role():
    for principal in (
        _course_principal("m1", "c1", "_maintainer"),
        _course_principal("o1", "c1", "_owner"),
        _workspace_user(),
    ):
        with pytest.raises(ForbiddenException):
            await cw.update_course_workspace_settings(
                "c1", CourseWorkspaceSettingsUpdate(), principal,
                make_db(), MagicMock(), _coder_settings(),
            )


@pytest.mark.asyncio
async def test_settings_put_unknown_course_is_404():
    with pytest.raises(NotFoundException):
        await cw.update_course_workspace_settings(
            "c1", CourseWorkspaceSettingsUpdate(), _maintainer(),
            make_db(course=None), MagicMock(), _coder_settings(),
        )


@pytest.mark.asyncio
async def test_settings_put_validates_added_names():
    client = _list_client(["vscode-workspace"])
    db = make_db()
    with pytest.raises(BadRequestException) as exc:
        await cw.update_course_workspace_settings(
            "c1", CourseWorkspaceSettingsUpdate(template_names=["nope-workspace"]),
            _maintainer(), db, client, _coder_settings(),
        )
    assert "does not exist" in str(exc.value)

    disabled_row = WorkspaceTemplateSettings(template_name="vscode-workspace", enabled=False)
    db = make_db(settings_row=disabled_row, disabled=["vscode-workspace"])
    with pytest.raises(BadRequestException) as exc:
        await cw.update_course_workspace_settings(
            "c1", CourseWorkspaceSettingsUpdate(template_names=["vscode-workspace"]),
            _maintainer(), db, client, _coder_settings(),
        )
    assert "globally disabled" in str(exc.value)


@pytest.mark.asyncio
async def test_settings_put_retains_disabled_names_without_coder():
    # The retained (already associated) disabled template triggers no
    # validation — Coder is never contacted when nothing is added.
    db = make_db(
        course_templates=[_tpl_row("c1", "bash-workspace")],
        disabled=["bash-workspace"],
        course_settings=None,
    )
    client = MagicMock()
    client.list_templates = AsyncMock(side_effect=AssertionError("Coder must not be called"))
    result = await cw.update_course_workspace_settings(
        "c1",
        CourseWorkspaceSettingsUpdate(
            template_names=["bash-workspace"], lecturer_provision_enabled=True,
        ),
        _maintainer(), db, client, _coder_settings(enabled=False),
    )
    assert result.can_manage is True
    assert result.lecturer_provision_enabled is True
    # Manager still sees the retained row, flagged disabled.
    assert [(t.template_name, t.enabled) for t in result.templates] == [
        ("bash-workspace", False)
    ]


@pytest.mark.asyncio
async def test_settings_put_needs_coder_for_added_names():
    db = make_db()
    client = MagicMock()
    client.list_templates = AsyncMock(side_effect=RuntimeError("down"))
    with pytest.raises(ServiceUnavailableException):
        await cw.update_course_workspace_settings(
            "c1", CourseWorkspaceSettingsUpdate(template_names=["vscode-workspace"]),
            _maintainer(), db, client, _coder_settings(),
        )


@pytest.mark.asyncio
async def test_settings_get_hides_disabled_from_members_keeps_for_managers():
    db = make_db(
        course_templates=[_tpl_row("c1", "vscode-workspace"), _tpl_row("c1", "bash-workspace")],
        disabled=["bash-workspace"],
    )
    client = _list_client(["vscode-workspace", "bash-workspace"])

    result = await cw.get_course_workspace_settings(
        "c1", _maintainer(), db, client, _coder_settings()
    )
    assert [(t.template_name, t.enabled) for t in result.templates] == [
        ("bash-workspace", False), ("vscode-workspace", True),
    ]
    assert result.can_manage is True
    assert [t.name for t in result.available] == ["vscode-workspace"]

    with patch.object(cw, "get_course_member_or_403", return_value=MagicMock()):
        result = await cw.get_course_workspace_settings(
            "c1", _course_principal("s1", "c1", "_student"), db, client, _coder_settings()
        )
    assert [t.template_name for t in result.templates] == ["vscode-workspace"]
    assert result.can_manage is False
    assert result.available is None


@pytest.mark.asyncio
async def test_settings_get_survives_coder_down():
    db = make_db(course_templates=[_tpl_row("c1", "vscode-workspace")])
    client = MagicMock()
    client.list_templates = AsyncMock(side_effect=RuntimeError("down"))
    result = await cw.get_course_workspace_settings(
        "c1", _maintainer(), db, client, _coder_settings()
    )
    assert result.templates[0].display_name is None
    assert result.templates[0].exists_in_coder is None
    assert result.available is None


# --- lecturer bulk provisioning -----------------------------------------------


def _member(member_id="m1", user_id="1111-2222"):
    member = MagicMock(spec=CourseMember)
    member.id = member_id
    member.user_id = user_id
    member.user = MagicMock()
    return member


def _bulk_db(**kwargs):
    kwargs.setdefault("course_templates", [_tpl_row("c1", "vscode-workspace")])
    kwargs.setdefault(
        "course_settings",
        CourseWorkspaceSettings(course_id="c1", lecturer_provision_enabled=True),
    )
    return make_db(**kwargs)


@pytest.mark.asyncio
async def test_bulk_provision_requires_flag_for_lecturers_not_managers(monkeypatch):
    request = StudentWorkspaceProvisionRequest(
        template_name="vscode-workspace", course_member_ids=["m1"],
    )
    db = _bulk_db(course_settings=None)  # flag never enabled
    with pytest.raises(ForbiddenException) as exc:
        await cw.provision_student_workspaces(
            "c1", request, _course_principal("l1", "c1", "_lecturer"),
            db, MagicMock(), MagicMock(), _coder_settings(),
        )
    assert "not enabled" in str(exc.value)

    # Managers bypass the flag; the unknown member surfaces per-item.
    result = await cw.provision_student_workspaces(
        "c1", request, _maintainer(), db, MagicMock(), MagicMock(), _coder_settings(),
    )
    assert result.failed == 1
    assert "Not a member" in result.outcomes[0].error


@pytest.mark.asyncio
async def test_bulk_provision_requires_lecturer_and_course_template():
    request = StudentWorkspaceProvisionRequest(
        template_name="vscode-workspace", course_member_ids=["m1"],
    )
    with pytest.raises(ForbiddenException):
        await cw.provision_student_workspaces(
            "c1", request, _course_principal("t1", "c1", "_tutor"),
            _bulk_db(), MagicMock(), MagicMock(), _coder_settings(),
        )

    bad_template = StudentWorkspaceProvisionRequest(
        template_name="bash-workspace", course_member_ids=["m1"],
    )
    with pytest.raises(BadRequestException):
        await cw.provision_student_workspaces(
            "c1", bad_template, _course_principal("l1", "c1", "_lecturer"),
            _bulk_db(), MagicMock(), MagicMock(), _coder_settings(),
        )


@pytest.mark.asyncio
async def test_bulk_provision_continues_past_failures_and_derives_name(monkeypatch):
    member = _member()
    db = _bulk_db(member_first=member)
    monkeypatch.setattr(cw, "get_user_email", lambda u: "s@example.org")
    monkeypatch.setattr(cw, "get_user_fullname", lambda u: "Student One")
    monkeypatch.setattr(
        cw, "mint_workspace_token",
        lambda *a, **k: MintResult(token="tok", new_token_id="nt1", superseded_ids=[]),
    )
    rollback = MagicMock()
    monkeypatch.setattr(cw, "rollback_workspace_token_rotation", rollback)

    client = MagicMock()
    provision_result = MagicMock()
    provision_result.workspace.name = "vscode-exam1"
    client.provision_workspace = AsyncMock(
        side_effect=[RuntimeError("boom"), provision_result]
    )

    request = StudentWorkspaceProvisionRequest(
        template_name="vscode-workspace",
        course_member_ids=["m1", "m2"],
        home_mode="scratch",
        label="Exam#1",
    )
    result = await cw.provision_student_workspaces(
        "c1", request, _course_principal("l1", "c1", "_lecturer"),
        db, MagicMock(), client, _coder_settings(),
    )
    assert result.failed == 1 and result.succeeded == 1
    assert result.outcomes[0].error == "boom"
    assert result.outcomes[1].workspace_name == "vscode-exam1"
    # The failed member's token rotation is rolled back (their workspace never
    # received the new token); the succeeded member's is kept.
    assert rollback.call_count == 1
    # Label is sanitized into the derived name; scratch home is passed through.
    _, call_kwargs = client.provision_workspace.call_args
    assert call_kwargs["workspace_name"] == "vscode-exam1"
    assert call_kwargs["home_mode"] == "scratch"


# --- lecturer delete gate -----------------------------------------------------


def _delete_client(template="vscode-workspace", home_mode="scratch"):
    client = MagicMock()
    details = MagicMock()
    details.workspace.template_name = template
    details.workspace.latest_build_id = "b1"
    client.get_workspace = AsyncMock(return_value=details)
    client._get_build_param = AsyncMock(return_value=home_mode)
    client.delete_workspace = AsyncMock(return_value=True)
    return client


@pytest.mark.asyncio
async def test_lecturer_deletes_scratch_but_not_shared_workspaces():
    db = _bulk_db(members=[_member(user_id="1111-2222")])
    lecturer = _course_principal("l1", "c1", "_lecturer")

    result = await cw.delete_student_workspace(
        "c1", "u1111-2222", "vscode-tmp", lecturer, db, _delete_client()
    )
    assert result.success is True

    with pytest.raises(ForbiddenException) as exc:
        await cw.delete_student_workspace(
            "c1", "u1111-2222", "vscode", lecturer, db,
            _delete_client(home_mode="shared"),
        )
    assert "throwaway" in str(exc.value)

    # Maintainers may delete shared-home workspaces of course members.
    result = await cw.delete_student_workspace(
        "c1", "u1111-2222", "vscode", _maintainer(), db,
        _delete_client(home_mode="shared"),
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_lecturer_delete_rejects_non_members_and_foreign_templates():
    db = _bulk_db(members=[_member(user_id="1111-2222")])
    lecturer = _course_principal("l1", "c1", "_lecturer")

    with pytest.raises(ForbiddenException):
        await cw.delete_student_workspace(
            "c1", "u9999-0000", "vscode-tmp", lecturer, db, _delete_client()
        )

    with pytest.raises(ForbiddenException):
        await cw.delete_student_workspace(
            "c1", "u1111-2222", "other", lecturer, db,
            _delete_client(template="other-workspace"),
        )
