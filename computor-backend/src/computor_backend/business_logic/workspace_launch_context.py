"""Authenticated, short-lived course navigation for a user's Coder workspace.

The context is intentionally separate from Coder's immutable provisioning
``course_id``. A reusable workspace can open course A and then course B without
a rebuild or a credential change. Neither global claims nor admin status grant
permission to write another user's navigation context.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from computor_types.coder import CoderWorkspace, WorkspaceLaunchContext
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from computor_backend.business_logic.course_workspaces import is_template_enabled
from computor_backend.coder.client import CoderClient
from computor_backend.coder.exceptions import CoderNotFoundError
from computor_backend.coder.naming import coder_username_matches_user
from computor_backend.exceptions import ForbiddenException, NotFoundException
from computor_backend.model.course import Course
from computor_backend.model.workspace import CourseWorkspaceTemplate
from computor_backend.permissions.course_access import get_course_member_or_403
from computor_backend.permissions.principal import Principal

LAUNCH_CONTEXT_TTL = 15 * 60


def _require_owner(username: str, permissions: Principal) -> str:
    user_id = permissions.get_user_id_or_throw()
    if not coder_username_matches_user(username, str(user_id)):
        raise ForbiddenException(detail="You may only open your own workspace course context.")
    return str(user_id)


async def _owned_workspace(
    username: str, workspace_name: str, permissions: Principal, client: CoderClient,
) -> tuple[str, CoderWorkspace]:
    user_id = _require_owner(username, permissions)
    details = await client.get_workspace(username, workspace_name)
    workspace = details.workspace
    # Check Coder's answer as well as the path. Never trust a supplied owner
    # name or an administrator's ability to retrieve arbitrary workspaces.
    if not workspace.owner_name or not coder_username_matches_user(
        workspace.owner_name, user_id
    ):
        raise ForbiddenException(detail="You may only open your own workspace course context.")
    return user_id, workspace


def _key(user_id: str, workspace_id: str) -> str:
    # The stable Coder UUID prevents a deleted/recreated workspace with the
    # same display name from inheriting a previous launch.
    return f"workspace-launch-context:{user_id}:{workspace_id}"


def _require_course(
    course_id: UUID, permissions: Principal, db: Session, workspace: CoderWorkspace,
) -> None:
    # This helper checks an actual membership row, even for administrators,
    # rather than accepting a possibly stale token's cached course claims.
    get_course_member_or_403(permissions, course_id, db)
    course = db.query(Course).filter(Course.id == str(course_id)).first()
    if course is None or course.archived_at is not None or course.visible is False:
        raise NotFoundException(detail="Course is not available.")
    template_name = workspace.template_name
    allowed = db.query(CourseWorkspaceTemplate).filter(
        CourseWorkspaceTemplate.course_id == str(course_id),
        CourseWorkspaceTemplate.template_name == template_name,
    ).first()
    if not template_name or allowed is None or not is_template_enabled(db, template_name):
        raise ForbiddenException(detail="This workspace template is not enabled for the course.")


async def set_workspace_launch_context(
    username: str, workspace_name: str, course_id: UUID, permissions: Principal,
    db: Session, client: CoderClient, redis: Redis,
) -> WorkspaceLaunchContext:
    """Replace this owner's navigation request, without starting/rebuilding."""
    try:
        user_id, workspace = await _owned_workspace(
            username, workspace_name, permissions, client
        )
    except CoderNotFoundError as exc:
        raise NotFoundException(detail="Workspace was not found.") from exc
    _require_course(course_id, permissions, db, workspace)
    context = WorkspaceLaunchContext(
        course_id=course_id,
        request_id=uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=LAUNCH_CONTEXT_TTL),
    )
    await redis.set(
        _key(user_id, workspace.id), context.model_dump_json(), ex=LAUNCH_CONTEXT_TTL
    )
    return context


async def get_workspace_launch_context(
    username: str, workspace_name: str, permissions: Principal,
    db: Session, client: CoderClient, redis: Redis,
) -> WorkspaceLaunchContext | None:
    """Read the latest still-authorized request; expired/revoked ones vanish."""
    try:
        user_id, workspace = await _owned_workspace(
            username, workspace_name, permissions, client
        )
    except CoderNotFoundError:
        return None
    key = _key(user_id, workspace.id)
    raw = await redis.get(key)
    if not raw:
        return None
    try:
        context = WorkspaceLaunchContext.model_validate_json(raw)
        now = datetime.now(timezone.utc)
        if context.expires_at.tzinfo is None or not (
            now < context.expires_at <= now + timedelta(seconds=LAUNCH_CONTEXT_TTL)
        ):
            raise ValueError("Expired or invalid launch context")
        _require_course(context.course_id, permissions, db, workspace)
    except (ValidationError, ValueError, ForbiddenException, NotFoundException):
        await redis.delete(key)
        return None
    return context
