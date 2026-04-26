"""
Shared post-create logic for course members.

This module contains the unified post-create hook that runs after a
CourseMember is created, regardless of whether it was created via
the CRUD endpoint or the import endpoint.
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session

from computor_backend.model.course import (
    CourseMember,
    Course,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.permissions.principal import Principal

logger = logging.getLogger(__name__)


def _should_skip_service_account(course_member: CourseMember, db: Session) -> bool:
    """
    Determine whether to skip post-create hooks for a service account.

    Service accounts are skipped unless their ServiceType has
    ``requires_workspace=True``, in which case workspace provisioning
    (e.g. a GitLab repo fork) proceeds normally.

    The User is fetched by ``user_id`` directly rather than via the
    ``course_member.user`` relationship, because in the import path the
    CourseMember is only ``flush()``-ed (not committed) when this runs
    and the relationship is not reliably populated. Going through the
    relationship caused the import path to incorrectly treat service
    users as non-service and trigger GitLab provisioning.

    Args:
        course_member: The course member to check
        db: Database session

    Returns:
        True if this is a service account that should be skipped
    """
    from computor_backend.model.auth import User
    from computor_backend.model.service import Service

    user = db.query(User).filter(User.id == course_member.user_id).first()
    if not user or not user.is_service:
        return False

    service = db.query(Service).filter(Service.user_id == course_member.user_id).first()
    if service and service.service_type and service.service_type.requires_workspace:
        logger.info(
            f"Service account {course_member.user_id} has service_type "
            f"'{service.service_type.path}' with requires_workspace=True — "
            "proceeding with post-create hooks"
        )
        return False

    logger.info(
        f"Skipping post-create hooks for service account {course_member.user_id} "
        "(service type does not require workspace provisioning)"
    )
    return True


def _ensure_student_profile(course_member: CourseMember, db: Session) -> None:
    """
    Create a StudentProfile if this is the user's first course membership
    in this organization.

    Users can have multiple StudentProfiles (one per organization).

    Args:
        course_member: The newly created course member
        db: Database session
    """
    from computor_backend.model.auth import StudentProfile

    try:
        course = db.query(Course).filter(
            Course.id == course_member.course_id
        ).first()

        if not course or not course.organization_id:
            return

        existing_profile = db.query(StudentProfile).filter(
            StudentProfile.user_id == course_member.user_id,
            StudentProfile.organization_id == course.organization_id,
        ).first()

        if existing_profile:
            logger.debug(
                f"StudentProfile already exists for user {course_member.user_id} "
                f"in organization {course.organization_id}"
            )
            return

        student_profile = StudentProfile(
            user_id=course_member.user_id,
            student_email=course_member.user.email,
            organization_id=course.organization_id,
            student_id=None,
        )
        db.add(student_profile)
        db.flush()
        logger.info(
            f"Created StudentProfile for user {course_member.user_id} "
            f"in organization {course.organization_id}"
        )
    except Exception as e:
        logger.error(
            f"Failed to create StudentProfile for course member "
            f"{course_member.id}: {e}",
            exc_info=True,
        )


async def course_member_post_create(
    course_member: CourseMember,
    db: Session,
    permissions: Optional[Principal] = None,
) -> Optional[str]:
    """
    Unified post-create hook for CourseMember.

    Runs after a CourseMember is created via either the CRUD endpoint or
    the import endpoint. Performs:

    1. Service account check (skips non-agent service accounts)
    2. StudentProfile creation (if first membership in this organization)
    3. Submission group provisioning
    4. Workflow trigger for GitLab repository creation

    Args:
        course_member: The newly created CourseMember (SQLAlchemy model)
        db: Database session
        permissions: Optional Principal for task tracking. When called from
                     the CrudRouter post_create hook, this is None and
                     created_by is derived from the CourseMember.

    Returns:
        workflow_id if task was submitted, None otherwise
    """
    if _should_skip_service_account(course_member, db):
        return None

    logger.info(
        f"Running post_create for course member {course_member.id} "
        f"(user: {course_member.user_id}, course: {course_member.course_id})"
    )

    # Step 1: Ensure StudentProfile exists
    _ensure_student_profile(course_member, db)

    # Step 2: Provision submission groups
    from computor_backend.repositories.submission_group_provisioning import (
        provision_submission_groups_for_user,
    )

    try:
        provision_submission_groups_for_user(
            user_id=course_member.user_id,
            course_id=course_member.course_id,
            db=db,
        )
        logger.info(
            f"Provisioned submission groups for course member {course_member.id}"
        )
    except Exception as e:
        logger.error(
            f"Failed to provision submission groups for course member "
            f"{course_member.id}: {e}"
        )

    # Step 3: Gather submission_group_ids for the workflow
    submission_groups = (
        db.query(SubmissionGroup)
        .join(
            SubmissionGroupMember,
            SubmissionGroupMember.submission_group_id == SubmissionGroup.id,
        )
        .filter(SubmissionGroupMember.course_member_id == course_member.id)
        .all()
    )
    submission_group_ids = [str(sg.id) for sg in submission_groups]
    logger.info(
        f"Found {len(submission_group_ids)} submission groups for "
        f"course member {course_member.id}"
    )

    # Step 4: Trigger StudentRepositoryCreationWorkflow
    try:
        from computor_backend.task_tracker import get_task_tracker
        from computor_types.tasks import TaskSubmission

        task_tracker = await get_task_tracker()

        task_submission = TaskSubmission(
            task_name="StudentRepositoryCreationWorkflow",
            parameters={
                "course_member_id": str(course_member.id),
                "course_id": str(course_member.course_id),
                "submission_group_ids": submission_group_ids,
                "is_team": False,
            },
            queue="computor-tasks",
        )

        course = db.query(Course).filter(
            Course.id == course_member.course_id
        ).first()
        org_id = (
            str(course.organization_id)
            if course and course.organization_id
            else None
        )

        created_by = (
            permissions.user_id
            if permissions
            else str(course_member.created_by or course_member.user_id)
        )

        workflow_id = await task_tracker.submit_and_track_task(
            task_submission=task_submission,
            created_by=created_by,
            user_id=str(course_member.user_id),
            course_id=str(course_member.course_id),
            organization_id=org_id,
            entity_type="course_member",
            entity_id=str(course_member.id),
            description=(
                f"Creating repository for "
                f"{course_member.user.email if course_member.user else 'course member'}"
            ),
        )
        logger.info(
            f"Triggered StudentRepositoryCreationWorkflow: {workflow_id} "
            f"for course member {course_member.id}"
        )
        return workflow_id
    except Exception as e:
        logger.error(
            f"Failed to trigger StudentRepositoryCreationWorkflow for "
            f"course member {course_member.id}: {e}",
            exc_info=True,
        )
        return None
