"""A reused workspace follows the requesting student's selected course.

The handoff is short-lived, scoped to the actual workspace, and revalidates
membership and template access rather than trusting a stale Redis value.
"""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.dialects.postgresql.psycopg2 import dialect as postgres_dialect
from sqlalchemy.orm import Session
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BooleanClauseList, False_, True_

import computor_backend.business_logic.workspace_launch_context as launch
from computor_backend.coder.exceptions import CoderWorkspaceNotFoundError
from computor_backend.coder.naming import encode_coder_username
from computor_backend.exceptions import ForbiddenException, NotFoundException
from computor_backend.model.course import Course, CourseMember, CourseContent
from computor_backend.model.deployment import CourseContentDeployment
from computor_backend.model.workspace import (
    CourseWorkspaceTemplate,
    WorkspaceTemplateSettings,
)
from computor_backend.permissions.course_access import get_course_member_or_403
from computor_backend.permissions.principal import Principal

USER_ID = "0232de59-e05d-4bc2-898f-b879c06abcde"
OTHER_ID = "7c9e6679-7425-40de-944b-e07fc1f90ae7"
COURSE_A = UUID("01882d3f-4b95-4c75-9b16-d60a5b2d8f31")
COURSE_B = UUID("5ef06519-b515-4158-8039-f28e5da5eed4")
OWNER = encode_coder_username(USER_ID)


def _matches(row, expression):
    """Evaluate this fixture's simple SQL equality/AND filters on its rows."""
    if isinstance(expression, BooleanClauseList):
        matches = [_matches(row, item) for item in expression.clauses]
        return all(matches) if expression.operator is operators.and_ else any(matches)
    actual = getattr(row, expression.left.key)
    expected = getattr(expression.right, "value", None)
    if isinstance(expression.right, (False_, True_)):
        expected = isinstance(expression.right, True_)
    if expression.operator is operators.in_op:
        return str(actual) in {str(value) for value in expected}
    if expression.operator in (operators.is_, operators.eq):
        return actual is expected if actual is None or expected is None else str(actual) == str(expected)
    if expression.operator in (operators.is_not, operators.ne):
        return not (actual is expected if actual is None or expected is None else str(actual) == str(expected))
    raise AssertionError(f"Unexpected fixture filter: {expression}")


def _db(rows):
    db = MagicMock()

    def query(model):
        model = getattr(model, "class_", model)
        filters = []
        q = MagicMock()

        def apply_filters(*criteria):
            filters.extend(criteria)
            return q

        q.filter.side_effect = apply_filters
        q.first.side_effect = lambda: next(
            (row for row in rows.get(model, []) if all(_matches(row, f) for f in filters)), None
        )
        return q

    db.query.side_effect = query
    return db


class MemoryRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    async def set(self, key, value, *, ex=None):
        self.values[key] = value
        self.expirations[key] = ex

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, key):
        self.values.pop(key, None)
        self.expirations.pop(key, None)


@pytest.fixture
def context(monkeypatch):
    courses = [SimpleNamespace(id=cid, visible=True, archived_at=None) for cid in (COURSE_A, COURSE_B)]
    templates = [SimpleNamespace(course_id=cid, template_name="vscode-workspace") for cid in (COURSE_A, COURSE_B)]
    rows = {Course: courses, CourseWorkspaceTemplate: templates, WorkspaceTemplateSettings: []}
    workspace = SimpleNamespace(id="workspace-1", owner_name=OWNER, template_name="vscode-workspace")
    client = SimpleNamespace(get_workspace=AsyncMock(return_value=SimpleNamespace(workspace=workspace)))
    membership = MagicMock(return_value=SimpleNamespace(user_id=USER_ID))
    monkeypatch.setattr(launch, "get_course_member_or_403", membership)
    return SimpleNamespace(
        permissions=Principal(user_id=USER_ID), db=_db(rows), redis=MemoryRedis(),
        workspace=workspace, client=client, membership=membership, rows=rows,
    )


async def _set(ctx, course_id=COURSE_A, username=OWNER):
    return await launch.set_workspace_launch_context(
        username, "vscode", course_id, ctx.permissions, ctx.db, ctx.client, ctx.redis
    )


async def _get(ctx, username=OWNER):
    return await launch.get_workspace_launch_context(
        username, "vscode", ctx.permissions, ctx.db, ctx.client, ctx.redis
    )


@pytest.mark.asyncio
async def test_reusing_a_workspace_replaces_the_course_and_request(context):
    first = await _set(context, COURSE_A)
    second = await _set(context, COURSE_B)
    restored = await _get(context)

    assert UUID(str(first.course_id)) == COURSE_A
    assert UUID(str(second.course_id)) == COURSE_B
    assert first.request_id != second.request_id
    assert restored == second
    context_key = f"workspace-launch-context:{USER_ID}:workspace-1"
    last_key = f"workspace-last-course:{USER_ID}:workspace-1"
    assert set(context.redis.values) == {context_key, last_key}
    assert context.redis.expirations[context_key] == 900
    assert datetime.now(timezone.utc) < second.expires_at <= datetime.now(timezone.utc) + timedelta(seconds=900)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["launch", "poll"])
async def test_uuid_context_works_with_native_membership_parameter_binding(context, monkeypatch, operation):
    """Use the real permission query and PostgreSQL model binding, without a DB.

    The model stores UUIDs as strings (as_uuid=False). An incoming Pydantic
    UUID must cross that boundary correctly on both POST and the later GET.
    """
    original_query = context.db.query.side_effect
    session = Session()

    class BindingQuery:
        def __init__(self, query):
            self.query = query

        def filter(self, *criteria):
            return BindingQuery(self.query.filter(*criteria))

        def first(self):
            dialect = postgres_dialect()
            compiled = self.query.statement.compile(dialect=dialect)
            for name, value in compiled.params.items():
                binding = compiled.binds[name]
                processor = binding.type.dialect_impl(dialect).bind_processor(dialect)
                if processor is not None:
                    # This is the same native processor called before the
                    # driver executes a real PostgreSQL membership query.
                    processor(value)
            return SimpleNamespace(user_id=USER_ID, course_id=COURSE_A)

    def query(model):
        if model is CourseMember:
            return BindingQuery(session.query(model))
        return original_query(model)

    context.db.query.side_effect = query
    monkeypatch.setattr(launch, "get_course_member_or_403", get_course_member_or_403)
    try:
        if operation == "launch":
            result = await _set(context)
        else:
            await context.redis.set(
                launch._key(USER_ID, context.workspace.id),
                json.dumps({
                    "course_id": str(COURSE_A),
                    "request_id": "96292e04-5989-4f29-a50f-5b0043b6ea81",
                    "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                }),
                ex=900,
            )
            result = await _get(context)
        assert result is not None
        assert result.course_id == COURSE_A
    finally:
        session.close()


@pytest.mark.asyncio
async def test_raw_principal_id_also_addresses_the_owners_workspace(context):
    stored = await _set(context, username=USER_ID)
    assert await _get(context, username=USER_ID) == stored


@pytest.mark.asyncio
@pytest.mark.parametrize("admin", [False, True])
async def test_another_users_workspace_is_forbidden_even_to_admins(context, admin):
    context.permissions = Principal(user_id=USER_ID, roles=["_admin"] if admin else [])
    with pytest.raises(ForbiddenException):
        await _set(context, username=encode_coder_username(OTHER_ID))
    with pytest.raises(ForbiddenException):
        await _get(context, username=encode_coder_username(OTHER_ID))
    assert not context.redis.values


@pytest.mark.asyncio
@pytest.mark.parametrize("admin", [False, True])
async def test_coder_owner_is_checked_in_addition_to_request_username(context, admin):
    context.permissions = Principal(user_id=USER_ID, roles=["_admin"] if admin else [])
    context.workspace.owner_name = encode_coder_username(OTHER_ID)
    with pytest.raises(ForbiddenException):
        await _set(context)
    with pytest.raises(ForbiddenException):
        await _get(context)
    assert not context.redis.values


@pytest.mark.asyncio
async def test_admin_still_needs_actual_course_membership(context):
    context.permissions = Principal(user_id=USER_ID, roles=["_admin"])
    context.membership.side_effect = ForbiddenException(detail="Membership revoked")
    with pytest.raises(ForbiddenException):
        await _set(context)
    assert not context.redis.values


@pytest.mark.asyncio
async def test_principal_without_user_identity_cannot_read_or_write_context(context):
    context.permissions = Principal(user_id=None)
    with pytest.raises(NotFoundException):
        await _set(context)
    with pytest.raises(NotFoundException):
        await _get(context)
    context.client.get_workspace.assert_not_awaited()
    assert not context.redis.values


@pytest.mark.asyncio
@pytest.mark.parametrize("course_change", ["missing", "hidden", "archived"])
async def test_launch_rejects_missing_or_unavailable_courses(context, course_change):
    if course_change == "missing":
        context.rows[Course].clear()
    elif course_change == "hidden":
        context.rows[Course][0].visible = False
    else:
        context.rows[Course][0].archived_at = datetime.now(timezone.utc)
    with pytest.raises(NotFoundException):
        await _set(context)
    assert not context.redis.values


@pytest.mark.asyncio
@pytest.mark.parametrize("template_change", ["mismatch", "disabled"])
async def test_launch_rejects_a_template_not_available_to_the_course(context, template_change):
    if template_change == "mismatch":
        context.workspace.template_name = "matlab-workspace"
    else:
        context.rows[WorkspaceTemplateSettings].append(
            SimpleNamespace(template_name="vscode-workspace", enabled=False)
        )
    with pytest.raises(ForbiddenException):
        await _set(context)
    assert not context.redis.values


@pytest.mark.asyncio
async def test_unknown_workspace_is_404_for_write_but_empty_for_poll(context):
    context.client.get_workspace.side_effect = CoderWorkspaceNotFoundError("vscode")
    with pytest.raises(NotFoundException):
        await _set(context)
    assert await _get(context) is None


@pytest.mark.asyncio
async def test_poll_without_launch_context_returns_none(context):
    assert await _get(context) is None


@pytest.mark.asyncio
async def test_recreated_workspace_does_not_inherit_the_deleted_workspaces_context(context):
    await _set(context)
    context.workspace.id = "workspace-2"
    assert await _get(context) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["membership", "hidden", "archived", "template", "disabled"])
async def test_poll_discards_context_when_course_access_is_revoked(context, change):
    await _set(context)
    if change == "membership":
        context.membership.side_effect = ForbiddenException(detail="Membership revoked")
    elif change == "hidden":
        context.rows[Course][0].visible = False
    elif change == "archived":
        context.rows[Course][0].archived_at = datetime.now(timezone.utc)
    elif change == "template":
        context.rows[CourseWorkspaceTemplate].clear()
    else:
        context.rows[WorkspaceTemplateSettings].append(
            SimpleNamespace(template_name="vscode-workspace", enabled=False)
        )
    assert await _get(context) is None
    # Only the request is discarded; the last-course hint is checked again on use.
    assert launch._key(USER_ID, "workspace-1") not in context.redis.values


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["invalid-json", "content-without-course", "expired", "too-far-future"])
async def test_poll_discards_invalid_or_expired_context(context, change):
    await _set(context)
    key = next(iter(context.redis.values))
    value = json.loads(context.redis.values[key])
    if change == "invalid-json":
        context.redis.values[key] = "{broken"
    else:
        if change == "content-without-course":
            # A context without a course is a language-only launch; one that
            # still names course content has lost its course.
            value.pop("course_id")
            value["course_content_id"] = str(COURSE_B)
        elif change == "expired":
            value["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        else:
            value["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        context.redis.values[key] = json.dumps(value)
    assert await _get(context) is None
    # Only the request is discarded; the last-course hint is checked again on use.
    assert launch._key(USER_ID, "workspace-1") not in context.redis.values


@pytest.mark.asyncio
async def test_last_course_outlives_the_launch_and_fills_the_own_listing(context):
    """The dashboard reopens the workspace in the last course from any browser
    (computor-org/issues#523), long after the 15-minute request has expired."""
    await _set(context, COURSE_A)
    await _set(context, COURSE_B)
    last_key = f"workspace-last-course:{USER_ID}:workspace-1"
    assert context.redis.values[last_key] == str(COURSE_B)
    assert context.redis.expirations[last_key] == launch.LAST_COURSE_TTL > 900

    await context.redis.delete(f"workspace-launch-context:{USER_ID}:workspace-1")
    listed = [SimpleNamespace(id="workspace-1", last_course_id=None),
              SimpleNamespace(id="workspace-2", last_course_id=None)]
    await launch.populate_last_courses(USER_ID, listed, context.redis)

    assert listed[0].last_course_id == str(COURSE_B)
    assert listed[1].last_course_id is None


@pytest.mark.asyncio
async def test_last_course_of_another_user_is_not_listed(context):
    await _set(context, COURSE_A)
    listed = [SimpleNamespace(id="workspace-1", last_course_id=None)]
    await launch.populate_last_courses(OTHER_ID, listed, context.redis)
    assert listed[0].last_course_id is None


@pytest.mark.parametrize("value", ["fr", "de-DE", "", 12])
def test_launch_request_rejects_unknown_interface_languages(value):
    from computor_types.coder import WorkspaceLaunchContextRequest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        WorkspaceLaunchContextRequest(course_id=COURSE_A, ui_language=value)


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["de", "en", None])
async def test_launch_interface_language_round_trips_without_changing_course(context, language):
    result = await launch.set_workspace_launch_context(
        OWNER, "vscode", COURSE_A, context.permissions, context.db,
        context.client, context.redis, ui_language=language,
    )
    assert result.ui_language == language
    assert (await _get(context)).ui_language == language
    assert (await _get(context)).course_id == COURSE_A


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["de", "en"])
async def test_launch_without_course_carries_only_the_reading_language(context, language):
    # Opening a workspace from the list names no course; its language must
    # still reach the workspace, or the editor guesses one of its own.
    from computor_types.coder import WorkspaceLaunchContextRequest

    request = WorkspaceLaunchContextRequest(ui_language=language)
    result = await launch.set_workspace_launch_context(
        OWNER, "vscode", request.course_id, context.permissions, context.db,
        context.client, context.redis, ui_language=request.ui_language,
    )
    restored = await _get(context)
    assert result.course_id is None and result.ui_language == language
    assert restored == result
    context.membership.assert_not_called()
    assert f"workspace-last-course:{USER_ID}:workspace-1" not in context.redis.values


@pytest.mark.asyncio
async def test_launch_without_course_keeps_the_last_course(context):
    await _set(context, COURSE_A)
    await launch.set_workspace_launch_context(
        OWNER, "vscode", None, context.permissions, context.db,
        context.client, context.redis, ui_language="en",
    )
    last_key = f"workspace-last-course:{USER_ID}:workspace-1"
    assert context.redis.values[last_key] == str(COURSE_A)


@pytest.mark.asyncio
async def test_launch_without_course_rejects_course_content(context):
    from computor_types.coder import WorkspaceLaunchContextRequest
    from pydantic import ValidationError
    from computor_backend.exceptions import BadRequestException

    with pytest.raises(ValidationError):
        WorkspaceLaunchContextRequest(course_content_id=COURSE_B, ui_language="de")
    with pytest.raises(BadRequestException):
        await launch.set_workspace_launch_context(
            OWNER, "vscode", None, context.permissions, context.db,
            context.client, context.redis, course_content_id=COURSE_B,
        )


@pytest.mark.asyncio
async def test_launch_without_course_still_needs_the_own_workspace(context):
    context.workspace.owner_name = encode_coder_username(OTHER_ID)
    with pytest.raises(ForbiddenException):
        await launch.set_workspace_launch_context(
            OWNER, "vscode", None, context.permissions, context.db,
            context.client, context.redis, ui_language="de",
        )


@pytest.mark.asyncio
async def test_old_launch_payload_without_interface_language_remains_readable(context):
    from computor_types.coder import WorkspaceLaunchContextRequest

    assert WorkspaceLaunchContextRequest(course_id=COURSE_A).ui_language is None
    await _set(context)
    key = f"workspace-launch-context:{USER_ID}:workspace-1"
    old = json.loads(context.redis.values[key])
    old.pop("ui_language")
    context.redis.values[key] = json.dumps(old)
    assert (await _get(context)).ui_language is None


@pytest.mark.asyncio
async def test_unknown_language_in_stored_context_is_discarded(context):
    await _set(context)
    key = f"workspace-launch-context:{USER_ID}:workspace-1"
    payload = json.loads(context.redis.values[key])
    payload["ui_language"] = "fr"
    context.redis.values[key] = json.dumps(payload)
    assert await _get(context) is None
    assert key not in context.redis.values


TARGET = UUID("a1111111-1111-4111-8111-111111111111")


def _assignment(ctx):
    target = SimpleNamespace(id=str(TARGET), course_id=str(COURSE_A), path="unit.exercise",
                             course_content_kind_id="assignment", is_submittable=True,
                             visible=None, archived_at=None)
    ctx.rows[CourseContent] = [target]
    deployment = SimpleNamespace(course_content_id=str(TARGET), deployed_at=datetime.now(timezone.utc),
                                 deployment_status="deployed")
    ctx.rows[CourseContentDeployment] = [deployment]
    return target, deployment


async def _set_target(ctx, target=TARGET):
    return await launch.set_workspace_launch_context(
        OWNER, "vscode", COURSE_A, ctx.permissions, ctx.db, ctx.client, ctx.redis,
        course_content_id=target,
    )


@pytest.mark.asyncio
async def test_exact_assignment_roundtrip_and_repeated_clicks_get_fresh_requests(context):
    _assignment(context)
    first = await _set_target(context)
    assert first.course_content_id == TARGET
    assert await _get(context) == first
    second = await _set_target(context)
    assert second.course_content_id == TARGET
    assert second.request_id != first.request_id
    assert await _get(context) == second
    # A generic course launch replaces the explicit target instead of reusing it.
    legacy = await _set(context)
    assert legacy.course_content_id is None
    assert await _get(context) == legacy


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", ["missing", "other-course", "unsupported-kind", "archived", "hidden", "hidden-parent", "unreleased", "unassigned"])
async def test_unavailable_assignment_is_rejected_on_write_and_revoked_on_read(context, invalid):
    target, deployment = _assignment(context)
    await _set_target(context)
    if invalid == "missing": context.rows[CourseContent] = []
    elif invalid == "other-course": target.course_id = str(COURSE_B)
    elif invalid == "unsupported-kind": target.course_content_kind_id = "unsupported"
    elif invalid == "archived": target.archived_at = datetime.now(timezone.utc)
    elif invalid == "hidden": target.visible = False
    elif invalid == "hidden-parent":
        context.rows[CourseContent].append(SimpleNamespace(id="parent", course_id=str(COURSE_A), path="unit", visible=False))
    elif invalid == "unreleased": deployment.deployed_at = None
    elif invalid == "unassigned": deployment.deployment_status = "unassigned"
    assert await _get(context) is None
    assert launch._key(USER_ID, context.workspace.id) not in context.redis.values
    with pytest.raises(NotFoundException): await _set_target(context)


@pytest.mark.asyncio
async def test_previously_released_assignment_remains_available_during_version_update(context):
    _, deployment = _assignment(context)
    deployment.deployment_status = "pending"
    assert (await _set_target(context)).course_content_id == TARGET


def test_assignment_target_request_rejects_invalid_uuid_and_preserves_null_legacy():
    from pydantic import ValidationError
    from computor_types.coder import WorkspaceLaunchContextRequest
    assert WorkspaceLaunchContextRequest(course_id=COURSE_A).course_content_id is None
    assert WorkspaceLaunchContextRequest(course_id=COURSE_A, course_content_id=None).course_content_id is None
    with pytest.raises(ValidationError):
        WorkspaceLaunchContextRequest(course_id=COURSE_A, course_content_id="not-an-id")


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", [None, "other-course", "hidden", "hidden-parent"])
async def test_unit_target_uses_native_student_visibility_without_assignment_release(context, invalid):
    target, _ = _assignment(context)
    target.course_content_kind_id = "unit"
    target.is_submittable = False
    context.rows[CourseContentDeployment] = []
    assert (await _set_target(context)).course_content_id == TARGET
    assert (await _get(context)).course_content_id == TARGET
    if invalid is None:
        return
    if invalid == "other-course":
        target.course_id = str(COURSE_B)
    elif invalid == "hidden":
        target.visible = False
    else:
        context.rows[CourseContent].append(SimpleNamespace(id="parent", course_id=str(COURSE_A), path="unit", visible=False))
    assert await _get(context) is None
    with pytest.raises(NotFoundException):
        await _set_target(context)
