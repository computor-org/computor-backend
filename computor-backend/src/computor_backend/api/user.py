from typing import Annotated, Optional, List
from uuid import UUID

import logging
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_types.course_member_accounts import (
    CourseMemberProviderAccountUpdate,
    CourseMemberReadinessStatus,
    CourseMemberValidationRequest,
)
from computor_types.users import UserGet, UserScopes
from computor_types.course_git import (
    CourseGitDescriptor,
    CourseMemberRepositoryGet,
    CourseMemberRepositoryRegister,
    StudentRepositoryProvisioned,
    TemplateAccessGet,
)
from computor_backend.permissions.auth import (
    ApiTokenCredentials,
    SSOAuthCredentials,
    get_current_principal,
    parse_authorization_header,
)
from computor_backend.permissions.principal import Principal
import httpx
from fastapi import APIRouter, Depends, Response

from computor_backend.exceptions import RateLimitException, ServiceUnavailableException
from computor_backend.redis_cache import get_redis_client
from computor_types.course_members import CourseMemberGet

# Import business logic
from computor_backend.business_logic.users import (
    get_current_user,
    get_user_scopes_from_principal,
    get_course_views_for_user,
    get_course_views_for_user_by_course,
)
from computor_backend.business_logic.course_accounts import (
    validate_user_course,
    register_user_course_account,
)
from computor_backend.business_logic.course_registration import (
    register_in_public_course,
)
from computor_backend.business_logic.course_git import (
    get_course_git_descriptor,
    get_student_repository,
    get_template_access,
    get_template_archive_source,
    provision_student_repository,
    register_byo_repository,
    register_gitlab_managed_access,
)

logger = logging.getLogger(__name__)

user_router = APIRouter()

@user_router.get("", response_model=UserGet)
def get_current_user_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """Get the current authenticated user."""
    return get_current_user(permissions.user_id, db)

@user_router.get(
    "/scopes",
    response_model=UserScopes,
)
async def get_current_user_scopes(
    permissions: Annotated[Principal, Depends(get_current_principal)],
):
    """Per-scope role memberships for the current user.

    Returns ``is_admin`` plus three maps (``organization``,
    ``course_family``, ``course``) keyed by scope_id, each listing the
    role labels the user holds on that scope. The client can use this
    to pre-gate UI against the same authorization data the server uses
    internally — e.g. only show the "Post organization message" button
    on orgs where the user has ``_owner``/``_manager``.

    Admins receive empty maps with ``is_admin=true``; treat that as
    "every role on every scope".
    """
    return get_user_scopes_from_principal(permissions)


@user_router.get(
    "/views",
    response_model=List[str],
)
async def get_course_views_for_current_user(
    permissions: Annotated[Principal, Depends(get_current_principal)],
):
    """Get available views for the current user.

    The ``lecturer`` view is the org → course-family → course creation
    pipeline plus the example library, so it is granted to ``_admin``,
    ``_organization_manager``, ``_example_manager``, any organization- or
    course-family-scoped role, and course lecturers (or higher). Computed
    purely from the principal — no DB hit.
    """
    if not permissions.get_user_id():
        return []

    return get_course_views_for_user(permissions)

@user_router.get(
    "/views/{course_id}",
    response_model=List[str],
)
async def get_course_views_for_current_user_by_course(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get available views based on role for a specific course for the current user.

    student/tutor/lecturer are course-role perspectives (membership-based). The
    ``management`` view is course administration (member management, …) and is
    granted to the lecturer cohort — admins, organization managers, and course
    lecturers or higher — even when they hold no student/tutor/lecturer role.
    """
    user_id = permissions.get_user_id()
    if not user_id:
        return []

    views = get_course_views_for_user_by_course(user_id, course_id, db)
    if (
        permissions.is_admin
        or "_organization_manager" in permissions.roles
        or "lecturer" in views
    ):
        views = sorted(set(views) | {"management"})
    return views

@user_router.get(
    "/courses/{course_id}/git",
    response_model=CourseGitDescriptor,
)
async def get_course_git_descriptor_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """How the current user obtains their repository for a course.

    Returns the course's git binding — delivery mode, allowed student-repo
    backends (Forgejo babysat / GitLab BYO / download), and the
    ``student-template`` location. Gated on course membership; returns an
    ``unconfigured`` descriptor when the course has no git binding yet.
    """
    return get_course_git_descriptor(course_id, permissions, db)


@user_router.get(
    "/courses/{course_id}/repository",
    response_model=Optional[CourseMemberRepositoryGet],
)
async def get_student_repository_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """The current student's repository for a course, or ``null`` if none yet.

    The babysitting "do I already have a repo?" check — returns the recorded
    repo (Forgejo babysat or BYO) without creating one. 404 only when the caller
    is not a member of the course.
    """
    return get_student_repository(course_id, permissions, db)


@user_router.post(
    "/courses/{course_id}/provision-repository",
    response_model=StudentRepositoryProvisioned,
)
async def provision_student_repository_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    rotate: bool = False,
    db: Session = Depends(get_db),
):
    """Babysat Forgejo provisioning for the current student.

    Forks the course's student-template into the student's own repository and
    records it. Idempotent — returns the existing repo if already provisioned.
    Also returns the repo-scoped Forgejo clone token (`clone_token` +
    `clone_username`) so `git clone`/push authenticates; it is never returned by
    `GET .../repository`. Requires the course to be bound to a managed Forgejo
    server offering the ``forgejo`` mode.

    The token is minted once and returned unchanged on later calls: Forgejo
    keeps one token per user and instance, so re-minting would break the copy
    stored in every repo the student has already cloned. Pass `rotate=true` to
    force a fresh one — the escape hatch when the credential stopped working —
    which invalidates the previous token, so the client must then update the
    remotes of all its clones on that server.
    """
    return provision_student_repository(course_id, permissions, db, rotate=rotate)


@user_router.post(
    "/courses/{course_id}/register-repository",
    response_model=CourseMemberRepositoryGet,
)
async def register_student_repository_endpoint(
    course_id: UUID | str,
    payload: CourseMemberRepositoryRegister,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Record where the current student's BYO repository lives (e.g. a GitLab
    repo created by the VSCode extension with the student's own PAT).

    Tracking only — the backend never reads the repo (grading is API upload).
    Upserts the per-membership record; the course must offer the given mode.
    """
    return register_byo_repository(course_id, payload, permissions, db)


@user_router.post(
    "/courses/{course_id}/register-gitlab",
    response_model=CourseMemberRepositoryGet,
)
async def register_gitlab_managed_endpoint(
    course_id: UUID | str,
    payload: CourseMemberValidationRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Register the current student's GitLab PAT for a managed-GitLab course and
    grant them access to their repository.

    ``GET /api/v4/user`` with the student's PAT proves their GitLab identity; the
    backend links the account and uses the registry's group token to add them as
    a Maintainer on their repo (Reporter on the template). Provisions the repo
    first if needed. Idempotent.
    """
    return register_gitlab_managed_access(
        course_id,
        payload.provider_access_token if payload else None,
        permissions,
        db,
    )


@user_router.post(
    "/courses/{course_id}/template-access",
    response_model=TemplateAccessGet,
)
async def template_access_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Mint a one-time READ-ONLY git credential for the course's template.

    Lets the current course member fetch the student-template over git — the
    extension uses it to seed an external repo with full history and to merge
    new template commits into the student's repo. The token is rotated on each
    call under its own name (never touching the provisioning clone token) and
    cannot push. `token` is null until the member's first git-server SSO login
    (re-call afterwards). Managed-Forgejo courses only.
    """
    return get_template_access(course_id, permissions, db)


@user_router.get("/courses/{course_id}/template/archive")
async def download_template_archive_endpoint(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Download the course template as a ZIP (download mode / external-repo seed).

    The backend fetches the template from the bound managed git server with its
    service token and returns the archive — the student never handles the token.
    Membership-gated.
    """
    url, headers, filename = get_template_archive_source(course_id, permissions, db)
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        upstream = await client.get(url, headers=headers)
    if upstream.status_code != 200:
        raise ServiceUnavailableException(
            detail="Could not fetch the template archive from the git server.",
            context={"upstream_status": upstream.status_code},
        )
    return Response(
        content=upstream.content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@user_router.post(
    "/courses/{course_id}/validate",
    response_model=CourseMemberReadinessStatus,
)
async def validate_current_user_course(
    course_id: UUID | str,
    validation: CourseMemberValidationRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Validate user's course membership and provider account."""
    return validate_user_course(
        course_id=course_id,
        provider_access_token=validation.provider_access_token if validation else None,
        permissions=permissions,
        db=db,
    )

@user_router.post(
    "/courses/{course_id}/register",
    response_model=CourseMemberReadinessStatus,
)
async def register_current_user_course_account(
    course_id: UUID | str,
    payload: CourseMemberProviderAccountUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Register user's provider account for a course."""
    return register_user_course_account(
        course_id=course_id,
        provider_account_id=payload.provider_account_id,
        provider_access_token=payload.provider_access_token,
        permissions=permissions,
        db=db,
    )


# Fixed window, per user, across ALL courses rather than per course: one
# registration provisions a SubmissionGroup per submittable content in the
# course, so the expensive case is a script walking the catalog, not repeated
# attempts at a single course.
REGISTRATION_LIMIT = 10
REGISTRATION_WINDOW = 3600


async def check_registration_rate_limit(user_id: str, cache) -> bool:
    """True once the user has spent their self-registration budget.

    Same shape as check_template_download_rate_limit in api/courses.py. Fails
    open: this bounds casual and accidental abuse, it is not a security
    control.
    """
    key = f"rate_limit:course_registration:{user_id}"
    try:
        count = await cache.incr(key)
        if count == 1:
            await cache.expire(key, REGISTRATION_WINDOW)
        return count > REGISTRATION_LIMIT
    except Exception as e:
        logger.error(f"Course registration rate limit check failed: {e}")
        return False


@user_router.post(
    "/courses/{course_id}/enroll",
    response_model=CourseMemberGet,
    status_code=201,
    summary="Enrol yourself as a student in a public course",
)
async def enroll_in_public_course(
    course_id: UUID | str,
    response: Response,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    credentials: Annotated[
        SSOAuthCredentials | ApiTokenCredentials,
        Depends(parse_authorization_header),
    ],
    db: Session = Depends(get_db),
    cache=Depends(get_redis_client),
):
    """Create your own ``_student`` membership in a public course.

    Named ``enroll`` rather than ``register`` because ``POST
    /user/courses/{course_id}/register`` above already means "register your git
    provider account for this course" — two unrelated meanings one letter apart
    would be a trap.

    The request has no body. The role is not a parameter: self-registration can
    only ever produce ``_student``, in the course's first existing group (or a
    ``default`` group created for the purpose). Idempotent — an existing
    membership of any role comes back unchanged with a 200, so a lecturer who
    clicks Enrol is not demoted. There is no matching DELETE; course staff
    remove members.

    404 when the course does not exist *or* is not public: a private course
    must not be distinguishable from a missing one.
    """
    user_id = permissions.get_user_id_or_throw()
    if await check_registration_rate_limit(str(user_id), cache):
        raise RateLimitException(
            error_code="RATE_001",
            detail="Too many course registrations. Please wait before trying again.",
            retry_after=REGISTRATION_WINDOW,
            context={
                "limit": REGISTRATION_LIMIT,
                "window_seconds": REGISTRATION_WINDOW,
            },
        )

    member, created = await register_in_public_course(course_id, permissions, db)

    if not created:
        response.status_code = 200
        return CourseMemberGet.model_validate(member, from_attributes=True)

    # A fresh membership must be visible to the caller NOW. Three caches would
    # otherwise hide it: the per-token Principal (AUTH_CACHE_TTL = 900 s), which
    # backs GET /user/scopes and therefore all client-side gating; the user's
    # course-membership permission cache; and the role-aware dashboard views.
    await _invalidate_after_enrollment(member, credentials, cache)

    return CourseMemberGet.model_validate(member, from_attributes=True)


async def _invalidate_after_enrollment(member, credentials, cache) -> None:
    """Best-effort cache busting; a stale cache must never fail a good write."""
    try:
        from computor_backend.business_logic.auth import (
            invalidate_principal_cache_for_token,
        )
        from computor_backend.business_logic.messages import invalidate_course_dashboards
        from computor_backend.permissions.cache import (
            invalidate_user_course_memberships_sync,
        )
        from computor_backend.redis_cache import get_cache

        await invalidate_principal_cache_for_token(credentials.token, cache)
        invalidate_user_course_memberships_sync(str(member.user_id))

        view_cache = get_cache()
        invalidate_course_dashboards(member.course_id, view_cache)
        view_cache.invalidate_user_views(user_id=str(member.user_id))
    except Exception as e:
        logger.warning(f"Cache invalidation after course enrollment failed: {e}")
