"""Course-scoped workspace configuration and template governance.

Owns three related concerns:

- the global per-template ``enabled`` switch and the running-seat quota
  (``workspace_template_settings``), shared with the coder API endpoints;
- the course → allowed-template association (``course_workspace_template``)
  plus course-level flags (``course_workspace_settings``), both governed by
  ``workspace:manage`` — course roles get read access only;
- lecturer bulk-provisioning of (throwaway) student workspaces when a course
  has ``lecturer_provision_enabled``.

Course members derive workspace access from the association: a ``_student``+
member of any course with at least one allowed AND globally enabled template
may list/self-provision/start/stop their own workspaces without holding a
global workspace role (see ``api/coder.py``).
"""
import asyncio
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from computor_backend.coder.client import CoderClient
from computor_backend.coder.config import CoderSettings
from computor_backend.coder.exceptions import CoderWorkspaceNotFoundError
from computor_backend.coder.naming import derive_workspace_name, sanitize_workspace_name
from computor_backend.coder.service import (
    derive_workspace_app_secret,
    get_user_email,
    get_user_fullname,
    mint_workspace_token,
    workspace_app_password_hash,
)
from computor_backend.exceptions import (
    BadRequestException,
    ComputorException,
    ConflictException,
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
from computor_backend.permissions.course_access import get_course_member_or_403
from computor_backend.permissions.principal import Principal
from computor_types.coder import CoderWorkspace, WorkspaceActionResponse
from computor_types.course_workspaces import (
    CourseStudentWorkspaceEntry,
    CourseStudentWorkspacesResponse,
    CourseWorkspaceAdminItem,
    CourseWorkspaceAdminListResponse,
    CourseWorkspaceSettingsGet,
    CourseWorkspaceSettingsUpdate,
    CourseWorkspaceTemplateItem,
    StudentWorkspaceProvisionOutcome,
    StudentWorkspaceProvisionRequest,
    StudentWorkspaceProvisionResponse,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Template governance (shared with api/coder.py)
# -----------------------------------------------------------------------------

# Builds counted against a template's max_running_workspaces quota: the
# latest build is a start whose job is queued, applying, or applied.
ACTIVE_BUILD_STATUSES = {"pending", "starting", "running", "succeeded"}


def template_settings_row(
    db: Session, template_name: str
) -> Optional[WorkspaceTemplateSettings]:
    return (
        db.query(WorkspaceTemplateSettings)
        .filter(WorkspaceTemplateSettings.template_name == template_name)
        .first()
    )


async def enforce_template_quota(
    db: Session,
    client: CoderClient,
    template_name: str,
    exclude_workspace_id: Optional[str] = None,
) -> None:
    """Reject provision/start when the template is at its running-seat cap.

    The cap counts running/starting workspaces of the template across ALL
    users and applies to everyone, admins included — it models hard capacity
    (e.g. MATLAB license seats), which exceeding would break anyway. A soft
    check (two racing starts can both pass), which is acceptable for a cap
    whose violation just means one container too many until the next stop.
    """
    row = template_settings_row(db, template_name)
    if row is None or row.max_running_workspaces is None:
        return
    limit = int(row.max_running_workspaces)
    workspaces = await client.list_all_workspaces()
    active = 0
    for workspace in workspaces:
        if workspace.template_name != template_name:
            continue
        if exclude_workspace_id and workspace.id == exclude_workspace_id:
            continue
        if workspace.latest_build_transition != "start":
            continue
        status = (
            workspace.latest_build_status.value if workspace.latest_build_status else ""
        )
        if status in ACTIVE_BUILD_STATUSES:
            active += 1
    if active >= limit:
        raise ConflictException(
            detail=(
                f"Template '{template_name}' is at its capacity of {limit} running "
                f"workspace(s) ({active} currently active). Stop an existing "
                "workspace or try again later."
            ),
        )


def get_disabled_template_names(
    db: Session, among: Optional[set[str]] = None
) -> set[str]:
    """Template names whose settings row has enabled = false.

    A template without a settings row counts as enabled (rows are lazily
    upserted). ``among`` restricts the lookup to the given names.
    """
    if among is not None and not among:
        return set()
    q = db.query(WorkspaceTemplateSettings.template_name).filter(
        WorkspaceTemplateSettings.enabled.is_(False)
    )
    if among is not None:
        q = q.filter(WorkspaceTemplateSettings.template_name.in_(list(among)))
    return {row[0] for row in q.all()}


def is_template_enabled(db: Session, template_name: str) -> bool:
    """No settings row means enabled."""
    row = template_settings_row(db, template_name)
    return True if row is None else bool(row.enabled)


# -----------------------------------------------------------------------------
# Root / internet policy
#
# Two levels, ANDed inside the Terraform template (see ops/coder/templates):
# the template settings row is the ceiling and travels as a --variable at push
# time; the course association row narrows it and travels as a rich parameter
# per workspace. Resolving the AND in the template rather than here means a
# rich parameter — the weaker, per-workspace input — can never widen access.
# -----------------------------------------------------------------------------

# Mirrors the templates' own variable defaults, so a template with no settings
# row behaves exactly like one with a freshly created row.
DEFAULT_ALLOW_ROOT = False
DEFAULT_ALLOW_INTERNET = True


def settings_row_policy(row: Optional[WorkspaceTemplateSettings]) -> tuple[bool, bool]:
    """(allow_root, allow_internet) of a settings row, or the defaults.

    Tolerates NULL attributes: the columns are NOT NULL in the database, but a
    row constructed in Python and not yet flushed has them unset, and
    ``bool(None)`` would silently read as "internet denied".
    """
    if row is None:
        return DEFAULT_ALLOW_ROOT, DEFAULT_ALLOW_INTERNET
    return (
        DEFAULT_ALLOW_ROOT if row.allow_root is None else bool(row.allow_root),
        DEFAULT_ALLOW_INTERNET if row.allow_internet is None else bool(row.allow_internet),
    )


def template_policy_ceiling(db: Session, template_name: str) -> tuple[bool, bool]:
    """(allow_root, allow_internet) a template permits at most."""
    return settings_row_policy(template_settings_row(db, template_name))


def course_template_policy(
    db: Session, course_id: UUID | str, template_name: str
) -> tuple[Optional[bool], Optional[bool]]:
    """One course's narrowing for a template; (None, None) = inherit."""
    row = (
        db.query(CourseWorkspaceTemplate)
        .filter(
            CourseWorkspaceTemplate.course_id == str(course_id),
            CourseWorkspaceTemplate.template_name == template_name,
        )
        .first()
    )
    if row is None:
        return None, None
    return row.allow_root, row.allow_internet


def member_template_policy(
    db: Session, principal: Principal, template_name: str
) -> tuple[Optional[bool], Optional[bool]]:
    """Narrowing for a self-provisioned workspace, across ALL the principal's
    courses that allow the template.

    The most restrictive course wins: a student enrolled in an exam course that
    denies internet does not get internet by launching the same template from
    another course. (None, None) when no course of theirs allows it — then only
    the template ceiling applies.
    """
    course_ids = principal.get_courses_with_role("_student")
    if not course_ids:
        return None, None
    rows = (
        db.query(CourseWorkspaceTemplate)
        .filter(
            CourseWorkspaceTemplate.course_id.in_([str(c) for c in course_ids]),
            CourseWorkspaceTemplate.template_name == template_name,
        )
        .all()
    )
    if not rows:
        return None, None
    # NULL means "this course adds no restriction", so only an explicit False counts.
    return (
        all(row.allow_root is not False for row in rows),
        all(row.allow_internet is not False for row in rows),
    )


def effective_policy(
    ceiling: bool, course_value: Optional[bool]
) -> bool:
    """What a workspace actually gets: the ceiling minus any course denial."""
    return ceiling and course_value is not False


def _narrowing(value: Optional[bool]) -> Optional[bool]:
    """Normalise a course policy value: only False is a statement."""
    return False if value is False else None


# -----------------------------------------------------------------------------
# Course-derived access
# -----------------------------------------------------------------------------

def get_member_course_template_names(db: Session, principal: Principal) -> set[str]:
    """Templates the principal may use through course membership.

    Union of the allowed templates of every course where the principal is
    ``_student``+ (from the in-memory claims, no DB), minus the globally
    disabled ones. Empty set = no course-derived workspace access.
    """
    course_ids = principal.get_courses_with_role("_student")
    if not course_ids:
        return set()
    names = {
        row[0]
        for row in db.query(CourseWorkspaceTemplate.template_name)
        .filter(CourseWorkspaceTemplate.course_id.in_([str(c) for c in course_ids]))
        .distinct()
        .all()
    }
    return names - get_disabled_template_names(db, among=names)


def can_manage_course_workspaces(principal: Principal) -> bool:
    """Course workspace config is governed by workspace maintainers only."""
    return principal.is_admin or principal.permitted("workspace", "manage")


# -----------------------------------------------------------------------------
# Course workspace settings (templates + flags)
# -----------------------------------------------------------------------------

def _load_course_or_404(db: Session, course_id: UUID | str) -> Course:
    course = db.query(Course).filter(Course.id == str(course_id)).first()
    if course is None:
        raise NotFoundException(detail=f"Course {course_id} not found")
    return course


def _course_template_rows(db: Session, course_id: UUID | str) -> list[CourseWorkspaceTemplate]:
    return (
        db.query(CourseWorkspaceTemplate)
        .filter(CourseWorkspaceTemplate.course_id == str(course_id))
        .order_by(CourseWorkspaceTemplate.template_name)
        .all()
    )


def _course_settings_row(db: Session, course_id: UUID | str) -> Optional[CourseWorkspaceSettings]:
    return (
        db.query(CourseWorkspaceSettings)
        .filter(CourseWorkspaceSettings.course_id == str(course_id))
        .first()
    )


def get_course_allowed_template_names(
    db: Session, course_id: UUID | str, *, enabled_only: bool = True
) -> set[str]:
    names = {row.template_name for row in _course_template_rows(db, course_id)}
    if enabled_only:
        names -= get_disabled_template_names(db, among=names)
    return names


async def _coder_templates_by_name(
    client: CoderClient, coder_settings: CoderSettings
) -> Optional[dict]:
    """Best-effort template map for enrichment; None when Coder is off/down."""
    if not coder_settings.enabled:
        return None
    try:
        return {t.name: t for t in await client.list_templates()}
    except Exception as e:
        logger.warning(f"Coder unreachable while enriching course templates: {e}")
        return None


async def get_course_workspace_settings(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
    client: CoderClient,
    coder_settings: CoderSettings,
) -> CourseWorkspaceSettingsGet:
    """A course's workspace configuration, shaped by the caller's rights.

    Managers see every association row plus the ``available`` picker list;
    course members see only globally enabled templates.
    """
    _load_course_or_404(db, course_id)
    is_manager = can_manage_course_workspaces(permissions)
    if not is_manager:
        get_course_member_or_403(
            permissions, str(course_id), db,
            detail="You must be a course member to view its workspace configuration",
        )

    rows = _course_template_rows(db, course_id)
    row_names = {row.template_name for row in rows}
    disabled = get_disabled_template_names(db, among=row_names)
    by_name = await _coder_templates_by_name(client, coder_settings)

    items: list[CourseWorkspaceTemplateItem] = []
    for row in rows:
        enabled = row.template_name not in disabled
        if not enabled and not is_manager:
            continue
        coder_template = (by_name or {}).get(row.template_name)
        ceiling_root, ceiling_internet = template_policy_ceiling(db, row.template_name)
        items.append(CourseWorkspaceTemplateItem(
            template_name=row.template_name,
            enabled=enabled,
            display_name=coder_template.display_name if coder_template else None,
            description=coder_template.description if coder_template else None,
            icon=coder_template.icon if coder_template else None,
            exists_in_coder=None if by_name is None else coder_template is not None,
            allow_root=row.allow_root,
            allow_internet=row.allow_internet,
            template_allow_root=ceiling_root,
            template_allow_internet=ceiling_internet,
            effective_allow_root=effective_policy(ceiling_root, row.allow_root),
            effective_allow_internet=effective_policy(ceiling_internet, row.allow_internet),
        ))

    available = None
    if is_manager and by_name is not None:
        all_disabled = get_disabled_template_names(db, among=set(by_name.keys()))
        available = [t for name, t in sorted(by_name.items()) if name not in all_disabled]

    settings_row = _course_settings_row(db, course_id)
    return CourseWorkspaceSettingsGet(
        course_id=str(course_id),
        templates=items,
        lecturer_provision_enabled=bool(
            settings_row.lecturer_provision_enabled if settings_row else False
        ),
        available=available,
        can_manage=is_manager,
    )


async def update_course_workspace_settings(
    course_id: UUID | str,
    data: CourseWorkspaceSettingsUpdate,
    permissions: Principal,
    db: Session,
    client: CoderClient,
    coder_settings: CoderSettings,
) -> CourseWorkspaceSettingsGet:
    """Replace a course's allowed-template list and flags (workspace:manage).

    Only *added* template names are validated (must exist in Coder and be
    globally enabled) — retained names skip validation so one later-disabled
    template cannot make the list unsaveable.
    """
    _load_course_or_404(db, course_id)
    if not can_manage_course_workspaces(permissions):
        raise ForbiddenException(
            detail="Managing course workspace templates requires the workspace maintainer role.",
        )

    requested: list[str] = []
    for name in data.template_names:
        name = (name or "").strip()
        if name and name not in requested:
            requested.append(name)

    current = {row.template_name for row in _course_template_rows(db, course_id)}
    added = [name for name in requested if name not in current]
    removed = current - set(requested)

    if added:
        by_name = await _coder_templates_by_name(client, coder_settings)
        if by_name is None:
            raise ServiceUnavailableException(
                detail="Coder is unavailable — cannot validate newly added templates.",
            )
        for name in added:
            if name not in by_name:
                raise BadRequestException(
                    detail=f"Template '{name}' does not exist in Coder.",
                )
            if not is_template_enabled(db, name):
                raise BadRequestException(
                    detail=f"Template '{name}' is globally disabled and cannot be added.",
                )

    if removed:
        (
            db.query(CourseWorkspaceTemplate)
            .filter(
                CourseWorkspaceTemplate.course_id == str(course_id),
                CourseWorkspaceTemplate.template_name.in_(list(removed)),
            )
            .delete(synchronize_session=False)
        )
    for name in added:
        db.add(CourseWorkspaceTemplate(
            course_id=str(course_id),
            template_name=name,
            created_by=permissions.user_id,
        ))
    db.flush()

    # Per-template narrowing. Applied to the whole retained list, not just the
    # additions: a policy row is a property of the association, so a template
    # missing from template_policies is reset to "inherit" rather than keeping
    # a stale denial the manager just cleared in the UI.
    for row in _course_template_rows(db, course_id):
        if row.template_name not in requested:
            continue
        policy = data.template_policies.get(row.template_name)
        # True is normalised to NULL: a course can only restrict, so "allow"
        # and "no opinion" are the same statement — storing True would read as
        # a grant the template may not honour.
        row.allow_root = _narrowing(policy.allow_root if policy else None)
        row.allow_internet = _narrowing(policy.allow_internet if policy else None)
        row.updated_by = permissions.user_id

    settings_row = _course_settings_row(db, course_id)
    if settings_row is None:
        settings_row = CourseWorkspaceSettings(
            course_id=str(course_id),
            created_by=permissions.user_id,
        )
        db.add(settings_row)
    settings_row.lecturer_provision_enabled = data.lecturer_provision_enabled
    settings_row.updated_by = permissions.user_id
    db.commit()

    return await get_course_workspace_settings(
        course_id, permissions, db, client, coder_settings
    )


def list_admin_course_workspaces(
    permissions: Principal, db: Session
) -> CourseWorkspaceAdminListResponse:
    """All courses with their workspace configuration, for the admin Courses tab.

    Deliberately claim-gated (workspace:manage) rather than membership-gated:
    workspace maintainers configure courses they are not members of.
    """
    if not can_manage_course_workspaces(permissions):
        raise ForbiddenException(
            detail="Workspace 'manage' permission required. Contact your administrator.",
        )
    courses = db.query(Course).order_by(Course.path).all()
    template_rows = db.query(CourseWorkspaceTemplate).all()
    settings_rows = db.query(CourseWorkspaceSettings).all()
    templates_by_course: dict[str, list[str]] = {}
    for row in template_rows:
        templates_by_course.setdefault(str(row.course_id), []).append(row.template_name)
    flags_by_course = {
        str(row.course_id): bool(row.lecturer_provision_enabled) for row in settings_rows
    }
    return CourseWorkspaceAdminListResponse(courses=[
        CourseWorkspaceAdminItem(
            course_id=str(course.id),
            title=course.title,
            path=str(course.path) if course.path is not None else None,
            template_names=sorted(templates_by_course.get(str(course.id), [])),
            lecturer_provision_enabled=flags_by_course.get(str(course.id), False),
        )
        for course in courses
    ])


# -----------------------------------------------------------------------------
# Lecturer bulk provisioning ("throwaway" workspaces)
# -----------------------------------------------------------------------------

def _require_course_lecturer(
    permissions: Principal, course_id: UUID | str
) -> bool:
    """Gate for the student-workspace endpoints.

    Returns True when the caller bypasses via admin/workspace:manage (such
    callers are also exempt from the lecturer_provision_enabled flag).
    """
    if can_manage_course_workspaces(permissions):
        return True
    if not permissions.has_course_role(str(course_id), "_lecturer"):
        raise ForbiddenException(
            detail="Managing student workspaces requires the course lecturer role.",
        )
    return False


def _member_for_owner_name(
    members: list[CourseMember], owner_name: Optional[str]
) -> Optional[CourseMember]:
    """Resolve a Coder owner username (u{uuid}, possibly truncated) to a member."""
    if not owner_name or not owner_name.startswith("u"):
        return None
    uid_prefix = owner_name[1:]
    if not uid_prefix:
        return None
    for member in members:
        if str(member.user_id).startswith(uid_prefix):
            return member
    return None


async def provision_student_workspaces(
    course_id: UUID | str,
    data: StudentWorkspaceProvisionRequest,
    permissions: Principal,
    db: Session,
    cache,
    client: CoderClient,
    coder_settings: CoderSettings,
) -> StudentWorkspaceProvisionResponse:
    """Provision one workspace per selected course member (lecturer feature).

    Sequential and per-item fault tolerant: one student failing (name
    conflict, missing email, seat quota) never aborts the batch. The
    workspace name carries a label suffix so it cannot collide with the
    student's self-provisioned per-template workspace.
    """
    _load_course_or_404(db, course_id)
    is_bypass = _require_course_lecturer(permissions, course_id)
    if not is_bypass:
        settings_row = _course_settings_row(db, course_id)
        if settings_row is None or not settings_row.lecturer_provision_enabled:
            raise ForbiddenException(
                detail="Lecturer workspace provisioning is not enabled for this course.",
            )

    template = data.template_name
    allowed = get_course_allowed_template_names(db, course_id, enabled_only=False)
    if template not in allowed:
        raise BadRequestException(
            detail=f"Template '{template}' is not allowed for this course.",
        )
    if not is_template_enabled(db, template):
        raise BadRequestException(
            detail=f"Template '{template}' is globally disabled.",
        )
    if not data.course_member_ids:
        raise BadRequestException(detail="No course members selected.")

    suffix = sanitize_workspace_name(data.label) if data.label else "tmp"
    if not suffix:
        raise BadRequestException(detail=f"Invalid label '{data.label}'.")
    workspace_name = sanitize_workspace_name(f"{derive_workspace_name(template)}-{suffix}")

    quota_row = template_settings_row(db, template)
    has_quota = quota_row is not None and quota_row.max_running_workspaces is not None

    # Same for every workspace in the batch: this course's narrowing of the
    # template's root/internet ceiling.
    policy_root, policy_internet = course_template_policy(db, course_id, template)

    outcomes: list[StudentWorkspaceProvisionOutcome] = []
    for member_id in data.course_member_ids:
        outcome = StudentWorkspaceProvisionOutcome(course_member_id=str(member_id))
        member = (
            db.query(CourseMember)
            .filter(
                CourseMember.id == str(member_id),
                CourseMember.course_id == str(course_id),
            )
            .first()
        )
        if member is None:
            outcome.error = "Not a member of this course"
            outcomes.append(outcome)
            continue
        user = member.user
        outcome.user_id = str(member.user_id)
        outcome.full_name = get_user_fullname(user)
        email = get_user_email(user)
        if not email:
            outcome.error = "User has no email address"
            outcomes.append(outcome)
            continue
        try:
            if has_quota:
                # Re-provisioning an existing workspace must not count itself.
                exclude_id = None
                try:
                    coder_user = await client._find_user_by_email(email)
                    existing = await client.get_user_workspaces(coder_user.username)
                    exclude_id = next(
                        (w.id for w in existing if w.name == workspace_name), None
                    )
                except CoderWorkspaceNotFoundError:
                    pass
                except Exception:
                    pass
                await enforce_template_quota(
                    db, client, template, exclude_workspace_id=exclude_id
                )
            token = mint_workspace_token(
                db, cache, str(member.user_id), str(permissions.user_id),
                workspace_name=workspace_name,
                ttl_days=coder_settings.workspace_token_ttl_days,
            )
            app_secret = derive_workspace_app_secret(str(member.user_id))
            result = await client.provision_workspace(
                user_email=email,
                username=str(member.user_id),
                full_name=get_user_fullname(user),
                template=template,
                workspace_name=workspace_name,
                computor_auth_token=token,
                home_mode=data.home_mode,
                allow_root=policy_root,
                allow_internet=policy_internet,
                app_secret=app_secret,
                app_password_hash=workspace_app_password_hash(app_secret),
                course_id=str(course_id),
            )
            outcome.workspace_name = result.workspace.name if result.workspace else workspace_name
            outcome.success = True
        except ComputorException as e:
            outcome.error = getattr(e, "detail", None) or str(e)
        except Exception as e:
            logger.warning(
                f"Bulk provisioning failed for member {member_id} in course {course_id}: {e}"
            )
            outcome.error = str(e) or "Provisioning failed"
        outcomes.append(outcome)

    succeeded = sum(1 for o in outcomes if o.success)
    return StudentWorkspaceProvisionResponse(
        outcomes=outcomes,
        succeeded=succeeded,
        failed=len(outcomes) - succeeded,
    )


async def _populate_build_params(
    client: CoderClient, workspaces: list[CoderWorkspace]
) -> dict[str, str]:
    """Fill CoderWorkspace.home_mode and return each workspace's course marker.

    One request per workspace for the whole parameter set rather than one per
    value — the API returns them all anyway. Bounded fan-out.
    """
    semaphore = asyncio.Semaphore(8)
    course_by_workspace: dict[str, str] = {}

    async def fill(workspace: CoderWorkspace) -> None:
        if not workspace.latest_build_id:
            return
        async with semaphore:
            try:
                params = await client.get_build_params(workspace.latest_build_id)
            except Exception:
                params = {}
        workspace.home_mode = params.get("home_mode")
        course = params.get("course_id")
        if course:
            course_by_workspace[workspace.id] = course

    await asyncio.gather(*(fill(w) for w in workspaces))
    return course_by_workspace


async def list_student_workspaces(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
    client: CoderClient,
) -> CourseStudentWorkspacesResponse:
    """Workspaces PROVISIONED FOR this course.

    Scoped on the course marker, not on (owner is a member) x (template is
    allowed): those two also match a member's personal workspace on a course
    template, which is none of the course's business and must not be listed
    here — the delete action next to each row acts on what this returns.

    Available to lecturers regardless of the provisioning flag so throwaway
    workspaces stay visible for cleanup after the flag is switched off.
    """
    _load_course_or_404(db, course_id)
    _require_course_lecturer(permissions, course_id)

    allowed = get_course_allowed_template_names(db, course_id, enabled_only=False)
    if not allowed:
        return CourseStudentWorkspacesResponse(students=[], count=0)

    members = (
        db.query(CourseMember)
        .filter(CourseMember.course_id == str(course_id))
        .all()
    )
    workspaces = await client.list_all_workspaces()

    # The cheap filters first: the marker costs one API call per workspace, so
    # only ask for candidates that could plausibly belong to this course.
    candidates: list[CoderWorkspace] = []
    member_of: dict[str, CourseMember] = {}
    for workspace in workspaces:
        if workspace.template_name not in allowed:
            continue
        member = _member_for_owner_name(members, workspace.owner_name)
        if member is None:
            continue
        candidates.append(workspace)
        member_of[workspace.id] = member

    course_by_workspace = await _populate_build_params(client, candidates)

    by_member: dict[str, list[CoderWorkspace]] = {}
    member_by_id = {str(m.id): m for m in members}
    relevant: list[CoderWorkspace] = []
    for workspace in candidates:
        if course_by_workspace.get(workspace.id) != str(course_id):
            continue
        by_member.setdefault(str(member_of[workspace.id].id), []).append(workspace)
        relevant.append(workspace)

    students = []
    for member_id, member_workspaces in sorted(by_member.items()):
        member = member_by_id[member_id]
        students.append(CourseStudentWorkspaceEntry(
            course_member_id=member_id,
            user_id=str(member.user_id),
            full_name=get_user_fullname(member.user),
            workspaces=sorted(member_workspaces, key=lambda w: w.name),
        ))
    students.sort(key=lambda s: (s.full_name or "", s.course_member_id))
    return CourseStudentWorkspacesResponse(students=students, count=len(relevant))


async def workspace_start_policy(
    db: Session, client: CoderClient, template_name: str, build_id: Optional[str]
) -> Optional[dict]:
    """The policy a workspace should start under, or None to leave it alone.

    A workspace carries its course marker, so the CURRENT course policy can be
    applied every time it starts. Without this a workspace that was stopped when
    a lecturer cut internet for an exam would come back with internet — the
    parameters it was created with are what a bare start carries forward.

    Returns None for a personal workspace (nothing to enforce) or when the
    marker cannot be read, so an unreachable Coder degrades to today's
    behaviour rather than to a policy guess.
    """
    if not build_id:
        return None
    try:
        params = await client.get_build_params(build_id)
    except Exception:
        return None
    course_id = params.get("course_id")
    if not course_id:
        return None
    course_root, course_internet = course_template_policy(db, course_id, template_name)
    # The template ceiling is applied inside Terraform; only the course's
    # narrowing travels as a parameter.
    return {
        "allow_root": course_root is not False,
        "allow_internet": course_internet is not False,
    }


async def apply_course_workspace_policy(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
    client: CoderClient,
) -> StudentWorkspaceProvisionResponse:
    """Push the course's current policy onto the workspaces it provisioned.

    Only RUNNING workspaces are rebuilt: their container was created with the
    old policy and nothing else can change it. Stopped ones are left alone and
    reported — they pick the policy up when they next start (see
    workspace_start_policy), which is both cheaper and less surprising than
    starting a student's workspace to lock it down.

    Governed by workspace:manage like the rest of the course workspace
    configuration.
    """
    _load_course_or_404(db, course_id)
    if not can_manage_course_workspaces(permissions):
        raise ForbiddenException(
            detail="Changing course workspace policy requires the workspace maintainer role.",
        )

    workspaces = await client.list_all_workspaces()
    outcomes: list[StudentWorkspaceProvisionOutcome] = []
    for workspace in workspaces:
        if not workspace.latest_build_id:
            continue
        try:
            params = await client.get_build_params(workspace.latest_build_id)
        except Exception:
            continue
        if params.get("course_id") != str(course_id):
            continue

        outcome = StudentWorkspaceProvisionOutcome(
            course_member_id="", workspace_name=workspace.name
        )
        running = (
            workspace.latest_build_transition == "start"
            and (workspace.latest_build_status.value if workspace.latest_build_status else "")
            in ACTIVE_BUILD_STATUSES
        )
        if not running:
            outcome.error = "Stopped — it will start under the new policy."
            outcomes.append(outcome)
            continue

        course_root, course_internet = course_template_policy(
            db, course_id, workspace.template_name or ""
        )
        ok = await client.rebuild_with_policy(workspace.id, {
            "allow_root": course_root is not False,
            "allow_internet": course_internet is not False,
        })
        outcome.success = ok
        if not ok:
            outcome.error = "Rebuild failed"
        outcomes.append(outcome)

    return StudentWorkspaceProvisionResponse(
        outcomes=outcomes,
        succeeded=sum(1 for o in outcomes if o.success),
        failed=sum(1 for o in outcomes if not o.success),
    )


async def delete_student_workspace(
    course_id: UUID | str,
    username: str,
    workspace_name: str,
    permissions: Principal,
    db: Session,
    client: CoderClient,
) -> WorkspaceActionResponse:
    """Delete a workspace that was provisioned for this course.

    Scoped on the course marker, for EVERY caller including admins. The
    workspace:manage bypass exempts a caller from the course's provisioning
    flag, never from the scope: a workspace that carries no marker (someone
    provisioned it for themselves) or another course's marker is not this
    course's to delete, and deleting one through a course-shaped UI was how
    a personal workspace got destroyed.

    Within the course, any of its workspaces may be deleted regardless of home
    mode. The previous rule — lecturers may delete scratch homes only — stood in
    for "the lecturer created it" and failed in both directions: it let this
    endpoint reach personal workspaces, and it blocked a lecturer from deleting
    a shared-home workspace they had bulk-provisioned themselves.

    The template list is deliberately NOT re-checked: the marker was stamped at
    provisioning time, when the template was allowed. Removing a template from
    the course afterwards must not strand the workspaces it already created.
    """
    _load_course_or_404(db, course_id)
    _require_course_lecturer(permissions, course_id)

    members = (
        db.query(CourseMember)
        .filter(CourseMember.course_id == str(course_id))
        .all()
    )
    member = _member_for_owner_name(members, username)
    if member is None:
        raise ForbiddenException(
            detail="The workspace owner is not a member of this course.",
        )

    try:
        details = await client.get_workspace(username, workspace_name)
    except CoderWorkspaceNotFoundError:
        raise NotFoundException(detail=f"Workspace '{workspace_name}' not found")

    workspace_course = None
    if details.workspace.latest_build_id:
        params = await client.get_build_params(details.workspace.latest_build_id)
        workspace_course = params.get("course_id")
    if workspace_course != str(course_id):
        raise ForbiddenException(
            detail=(
                "This workspace was not provisioned for this course. Personal "
                "workspaces can only be managed by their owner or under "
                "workspace administration."
            ),
        )

    success = await client.delete_workspace(username, workspace_name)
    return WorkspaceActionResponse(
        success=success,
        message="Workspace deleted" if success else "Failed to delete workspace",
    )
