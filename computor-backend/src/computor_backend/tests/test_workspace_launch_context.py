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
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BooleanClauseList, False_, True_

import computor_backend.business_logic.workspace_launch_context as launch
from computor_backend.coder.exceptions import CoderWorkspaceNotFoundError
from computor_backend.coder.naming import encode_coder_username
from computor_backend.exceptions import ForbiddenException, NotFoundException
from computor_backend.model.course import Course
from computor_backend.model.workspace import (
    CourseWorkspaceTemplate,
    WorkspaceTemplateSettings,
)
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
    if expression.operator in (operators.is_, operators.eq):
        return actual is expected if actual is None or expected is None else str(actual) == str(expected)
    if expression.operator in (operators.is_not, operators.ne):
        return not (actual is expected if actual is None or expected is None else str(actual) == str(expected))
    raise AssertionError(f"Unexpected fixture filter: {expression}")


def _db(rows):
    db = MagicMock()

    def query(model):
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
    assert len(context.redis.values) == 1
    assert list(context.redis.expirations.values()) == [900]
    assert datetime.now(timezone.utc) < second.expires_at <= datetime.now(timezone.utc) + timedelta(seconds=900)


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
    assert not context.redis.values


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["invalid-json", "missing-course", "expired", "too-far-future"])
async def test_poll_discards_invalid_or_expired_context(context, change):
    await _set(context)
    key = next(iter(context.redis.values))
    value = json.loads(context.redis.values[key])
    if change == "invalid-json":
        context.redis.values[key] = "{broken"
    else:
        if change == "missing-course":
            value.pop("course_id")
        elif change == "expired":
            value["expires_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        else:
            value["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        context.redis.values[key] = json.dumps(value)
    assert await _get(context) is None
    assert not context.redis.values
