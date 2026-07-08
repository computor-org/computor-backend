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
)
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
import httpx
from fastapi import APIRouter, Depends, Response

from computor_backend.exceptions import ServiceUnavailableException

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
from computor_backend.business_logic.course_git import (
    get_course_git_descriptor,
    get_student_repository,
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
    db: Session = Depends(get_db),
):
    """Babysat Forgejo provisioning for the current student.

    Forks the course's student-template into the student's own repository and
    records it. Idempotent — returns the existing repo if already provisioned.
    Also returns a **one-time** repo-scoped Forgejo clone token (`clone_token` +
    `clone_username`) so `git clone`/push authenticates; it is rotated on each
    call and never returned by `GET .../repository`. Requires the course to be
    bound to a managed Forgejo server offering the ``forgejo`` mode.
    """
    return provision_student_repository(course_id, permissions, db)


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
