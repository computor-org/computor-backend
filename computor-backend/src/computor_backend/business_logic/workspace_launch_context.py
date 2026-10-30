"""Authenticated, short-lived course navigation for a user's Coder workspace.

The context is intentionally separate from Coder's immutable provisioning
``course_id``. A reusable workspace can open course A and then course B without
a rebuild or a credential change. Neither global claims nor admin status grant
permission to write another user's navigation context.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4

from computor_types.coder import CoderWorkspace, WorkspaceLaunchContext
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.orm import Session

from computor_backend.business_logic.course_workspaces import is_template_enabled
from computor_backend.business_logic.content_visibility import is_student_visible
from computor_backend.coder.client import CoderClient
from computor_backend.coder.exceptions import CoderNotFoundError
from computor_backend.coder.naming import coder_username_matches_user
from computor_backend.exceptions import BadRequestException, ForbiddenException, NotFoundException
from computor_backend.model.course import Course, CourseContent
from computor_backend.model.workspace import CourseWorkspaceTemplate
from computor_backend.permissions.course_access import get_course_member_or_403
from computor_backend.permissions.principal import Principal

LAUNCH_CONTEXT_TTL = 15 * 60
# How long the dashboard remembers which course a workspace was last opened
# for. A convenience: once it is gone, the workspace opens without a course.
LAST_COURSE_TTL = 180 * 24 * 60 * 60


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


def _last_course_key(user_id: str, workspace_id: str) -> str:
    return f"workspace-last-course:{user_id}:{workspace_id}"


def _require_course(
    course_id: UUID, permissions: Principal, db: Session, workspace: CoderWorkspace,
) -> Course:
    # This helper checks an actual membership row, even for administrators,
    # rather than accepting a possibly stale token's cached course claims.
    # PostgreSQL UUID columns use as_uuid=False: keep API DTOs typed as UUID,
    # but pass their string form to all database filters, including membership.
    course_key = str(course_id)
    get_course_member_or_403(permissions, course_key, db)
    course = db.query(Course).filter(Course.id == course_key).first()
    if course is None or course.archived_at is not None or course.visible is False:
        raise NotFoundException(detail="Course is not available.")
    template_name = workspace.template_name
    allowed = db.query(CourseWorkspaceTemplate).filter(
        CourseWorkspaceTemplate.course_id == course_key,
        CourseWorkspaceTemplate.template_name == template_name,
    ).first()
    if not template_name or allowed is None or not is_template_enabled(db, template_name):
        raise ForbiddenException(detail="This workspace template is not enabled for the course.")
    return course


def _require_target(
    course_id: UUID, course_content_id: UUID | None, db: Session, course: Course,
) -> None:
    if course_content_id is None:
        return
    target = db.query(CourseContent).filter(
        CourseContent.id == str(course_content_id),
        CourseContent.course_id == str(course_id),
    ).first()
    # This is learner navigation, even when the caller also has staff claims.
    # Use the student visibility/release authority, including ancestor vetoes.
    if (target is None or target.course_content_kind_id not in {"assignment", "unit"}
            or target.archived_at is not None or not is_student_visible(db, target, course=course)):
        raise NotFoundException(detail="Course content is not available.")


async def set_workspace_launch_context(
    username: str, workspace_name: str, course_id: UUID | None, permissions: Principal,
    db: Session, client: CoderClient, redis: Redis,
    ui_language: Literal["de", "en"] | None = None,
    course_content_id: UUID | None = None,
) -> WorkspaceLaunchContext:
    """Replace this owner's navigation request, without starting/rebuilding.

    Without a course the request carries only the reading language: a
    workspace opened from the list must still read in the browser's language.
    """
    if course_id is None and course_content_id is not None:
        raise BadRequestException(detail="Course content needs its course.")
    try:
        user_id, workspace = await _owned_workspace(
            username, workspace_name, permissions, client
        )
    except CoderNotFoundError as exc:
        raise NotFoundException(detail="Workspace was not found.") from exc
    if course_id is not None:
        course = _require_course(course_id, permissions, db, workspace)
        _require_target(course_id, course_content_id, db, course)
    context = WorkspaceLaunchContext(
        course_id=course_id,
        course_content_id=course_content_id,
        ui_language=ui_language,
        request_id=uuid4(),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=LAUNCH_CONTEXT_TTL),
    )
    await redis.set(
        _key(user_id, workspace.id), context.model_dump_json(), ex=LAUNCH_CONTEXT_TTL
    )
    # Unlike the request above, this survives the launch, so the dashboard can
    # reopen the workspace in the same course from any browser.
    if course_id is not None:
        await redis.set(
            _last_course_key(user_id, workspace.id), str(course_id), ex=LAST_COURSE_TTL
        )
    return context


async def populate_last_courses(
    user_id: str, workspaces: list[CoderWorkspace], redis: Redis,
) -> None:
    """Fill ``CoderWorkspace.last_course_id`` on the user's own workspaces.

    Only a hint for choosing the course to open: the launch page posts it as a
    new launch context, which checks membership and template access again.
    """
    for workspace in workspaces:
        try:
            raw = await redis.get(_last_course_key(user_id, workspace.id))
        except Exception:
            raw = None
        if raw:
            workspace.last_course_id = raw.decode() if isinstance(raw, bytes) else str(raw)


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
        if context.course_id is not None:
            course = _require_course(context.course_id, permissions, db, workspace)
            _require_target(context.course_id, context.course_content_id, db, course)
        elif context.course_content_id is not None:
            raise ValueError("Course content without its course")
    except (ValidationError, ValueError, ForbiddenException, NotFoundException):
        await redis.delete(key)
        return None
    return context
