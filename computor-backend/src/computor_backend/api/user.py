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
from computor_types.users import UserGet, UserPassword
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.model.course import Course, CourseMember
from computor_backend.model.organization import Organization
from fastapi import APIRouter, Depends

# Import business logic
from computor_backend.business_logic.users import (
    get_current_user,
    set_user_password,
    get_course_views_for_user,
    get_course_views_for_user_by_course,
    validate_user_course,
    register_user_course_account,
    trigger_permission_grant_workflow,
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

@user_router.post("/password", status_code=204)
def set_user_password_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    payload: UserPassword,
    db: Session = Depends(get_db)
):
    """Set or update user password."""
    set_user_password(
        target_username=payload.username,
        new_password=payload.password,
        old_password=payload.password_old,
        permissions=permissions,
        db=db,
    )

@user_router.get(
    "/views",
    response_model=List[str],
)
async def get_course_views_for_current_user(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get available views based on roles across all courses for the current user."""
    user_id = permissions.get_user_id()
    if not user_id:
        return []

    return get_course_views_for_user(user_id, db)

@user_router.get(
    "/views/{course_id}",
    response_model=List[str],
)
async def get_course_views_for_current_user_by_course(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get available views based on role for a specific course for the current user."""
    user_id = permissions.get_user_id()
    if not user_id:
        return []

    return get_course_views_for_user_by_course(user_id, course_id, db)

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
    result = validate_user_course(
        course_id=course_id,
        provider_access_token=validation.provider_access_token if validation else None,
        permissions=permissions,
        db=db,
    )

    # If inline GitLab sync failed, trigger the Temporal workflow as a safety net
    await _trigger_permission_workflow_if_needed(
        course_id, permissions, db
    )

    return result

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
    result = register_user_course_account(
        course_id=course_id,
        provider_account_id=payload.provider_account_id,
        provider_access_token=payload.provider_access_token,
        permissions=permissions,
        db=db,
    )

    # If inline GitLab sync failed, trigger the Temporal workflow as a safety net
    await _trigger_permission_workflow_if_needed(
        course_id, permissions, db
    )

    return result


async def _trigger_permission_workflow_if_needed(
    course_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Trigger GitLab permission workflows for all courses on the same GitLab realm.

    When a student registers their GitLab account for one course, this checks ALL
    courses the user belongs to on the same GitLab instance and triggers the
    permission workflow for any with status 'pending' or 'sync_failed'.
    """
    try:
        # Find the GitLab URL for the current course's organization
        course = (
            db.query(Course)
            .filter(Course.id == str(course_id))
            .first()
        )
        if not course:
            return

        organization = (
            db.query(Organization)
            .filter(Organization.id == course.organization_id)
            .first()
        )
        if not organization:
            return

        gitlab_url = (organization.properties or {}).get("gitlab", {}).get("url")
        if not gitlab_url:
            return

        # Find all organizations on the same GitLab realm
        all_orgs = db.query(Organization).all()
        same_realm_org_ids = [
            str(org.id) for org in all_orgs
            if (org.properties or {}).get("gitlab", {}).get("url") == gitlab_url
        ]

        # Find all courses belonging to those organizations
        same_realm_course_ids = [
            str(c.id) for c in db.query(Course)
            .filter(Course.organization_id.in_(same_realm_org_ids))
            .all()
        ]

        # Find all CourseMember records for this user across those courses
        members = (
            db.query(CourseMember)
            .filter(
                CourseMember.user_id == permissions.user_id,
                CourseMember.course_id.in_(same_realm_course_ids),
            )
            .all()
        )

        for member in members:
            status = (member.properties or {}).get("gitlab_permissions_status")
            if status not in ("pending", "sync_failed"):
                continue

            # Only trigger if a repo exists (full_path is set)
            full_path = (member.properties or {}).get("gitlab", {}).get("full_path")
            if not full_path:
                continue

            workflow_id = await trigger_permission_grant_workflow(
                member, db, permissions.user_id
            )
            if workflow_id:
                logger.info(
                    "Triggered permission workflow %s for user %s in course %s (status was %s)",
                    workflow_id, permissions.user_id, member.course_id, status,
                )

    except Exception as exc:
        logger.error("Failed to trigger permission workflows: %s", exc)
