"""Backend CourseMember interface with SQLAlchemy model."""

from typing import Optional, Any
from uuid import UUID
from sqlalchemy.orm import Session
import logging

from computor_types.course_members import (
    CourseMemberInterface as CourseMemberInterfaceBase,
    CourseMemberQuery,
    CourseMemberUpdate,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseMember, SubmissionGroup, SubmissionGroupMember
from computor_backend.permissions.principal import Principal, course_role_hierarchy
from computor_backend.api.exceptions import ForbiddenException

logger = logging.getLogger(__name__)


async def post_create_course_member(course_member: CourseMember, db: Session):
    """
    Post-create hook for CourseMember.

    1. Creates StudentProfile if this is the first course membership in this organization
    2. Creates submission groups for all submittable course contents with max_group_size=1 or None
    3. Triggers the StudentRepositoryCreationWorkflow to create GitLab repository

    Args:
        course_member: The newly created course member
        db: Database session
    """
    # Only process for actual users (not service accounts)
    if course_member.user.is_service:
        logger.info(f"Skipping post_create for service account course member {course_member.id}")
        return

    logger.info(f"Running post_create for course member {course_member.id} (user: {course_member.user_id}, course: {course_member.course_id})")

    # Step 1: Create StudentProfile if this is the first course membership in this organization
    from computor_backend.model.auth import StudentProfile
    from computor_backend.model.course import Course

    try:
        # Get the course to find the organization_id
        course = db.query(Course).filter(Course.id == course_member.course_id).first()
        if course and course.organization_id:
            # Check if user already has a student profile for THIS organization
            # Note: Users can have multiple student profiles (one per organization)
            existing_profile = db.query(StudentProfile).filter(
                StudentProfile.user_id == course_member.user_id,
                StudentProfile.organization_id == course.organization_id
            ).first()

            if not existing_profile:
                # Create new student profile with user's email for this organization
                student_profile = StudentProfile(
                    user_id=course_member.user_id,
                    student_email=course_member.user.email,
                    organization_id=course.organization_id,
                    # student_id can be set later via course import or manual update
                    student_id=None,
                )
                db.add(student_profile)
                db.flush()
                logger.info(
                    f"Created StudentProfile for user {course_member.user_id} "
                    f"in organization {course.organization_id} (first course membership in this org)"
                )
            else:
                logger.debug(
                    f"StudentProfile already exists for user {course_member.user_id} "
                    f"in organization {course.organization_id}"
                )
    except Exception as e:
        logger.error(
            f"Failed to create StudentProfile for course member {course_member.id}: {e}",
            exc_info=True
        )
        # Don't fail the entire course member creation if StudentProfile creation fails

    # Provision submission groups for individual assignments (max_group_size=1 or None)
    from computor_backend.repositories.submission_group_provisioning import provision_submission_groups_for_user

    try:
        provision_submission_groups_for_user(
            user_id=course_member.user_id,
            course_id=course_member.course_id,
            db=db
        )
        logger.info(f"Provisioned submission groups for course member {course_member.id}")
    except Exception as e:
        logger.error(f"Failed to provision submission groups for course member {course_member.id}: {e}")
        # Don't fail the entire course member creation if provisioning fails

    # Get all submission group IDs for this course member
    submission_groups = (
        db.query(SubmissionGroup)
        .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
        .filter(SubmissionGroupMember.course_member_id == course_member.id)
        .all()
    )

    submission_group_ids = [str(sg.id) for sg in submission_groups]
    logger.info(f"Found {len(submission_group_ids)} submission groups for course member {course_member.id}")

    # Trigger StudentRepositoryCreationWorkflow with task tracking
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
                "is_team": False
            },
            queue="computor-tasks"
        )

        # Get organization_id from course for permission tracking
        org_id = str(course.organization_id) if course and course.organization_id else None

        workflow_id = await task_tracker.submit_and_track_task(
            task_submission=task_submission,
            created_by=str(course_member.created_by) if course_member.created_by else str(course_member.user_id),
            user_id=str(course_member.user_id),
            course_id=str(course_member.course_id),
            organization_id=org_id,
            entity_type="course_member",
            entity_id=str(course_member.id),
            description=f"Creating repository for course member {course_member.user.email}"
        )
        logger.info(f"Triggered StudentRepositoryCreationWorkflow: {workflow_id} for course member {course_member.id}")
    except Exception as e:
        logger.error(f"Failed to trigger StudentRepositoryCreationWorkflow for course member {course_member.id}: {e}")
        # Don't fail the course member creation if workflow submission fails


def custom_permissions_course_member(
    permissions: Principal,
    db: Session,
    id: UUID,
    entity: CourseMemberUpdate
):
    """
    Custom permission check for CourseMember updates.
    Replaces generic check_permissions to enforce course-role-based authorization.

    Validates:
    1. User has at least _lecturer role in the course
    2. User can only assign roles <= their own level
    3. User cannot modify their own role (unless admin)

    Args:
        permissions: Current user's permission context
        db: Database session
        id: CourseMember ID being updated
        entity: Update data

    Returns:
        SQLAlchemy query filtered to the target course member

    Raises:
        ForbiddenException: If permission denied
    """
    # Admin bypasses all checks
    if permissions.is_admin:
        return db.query(CourseMember)

    # Get the course member being updated
    course_member = db.query(CourseMember).filter(CourseMember.id == id).first()
    if not course_member:
        # Return query that will find nothing - let crud.py handle NotFoundException
        return db.query(CourseMember).filter(CourseMember.id == id)

    course_id = str(course_member.course_id)

    # Check user has at least _lecturer role in this course
    user_role = permissions.get_highest_course_role(course_id)
    if not user_role or course_role_hierarchy.get_role_level(user_role) < course_role_hierarchy.get_role_level("_lecturer"):
        raise ForbiddenException(
            "You don't have permission to update course members. "
            "Lecturer role or higher is required."
        )

    # Check if trying to modify their own course role
    if str(course_member.user_id) == permissions.user_id:
        raise ForbiddenException(
            "You cannot modify your own course membership. Please contact an administrator."
        )

    # Check if target course member has equal or higher role - cannot modify peers or superiors
    target_current_role = course_member.course_role_id
    if target_current_role:
        target_current_level = course_role_hierarchy.get_role_level(target_current_role)
        user_level = course_role_hierarchy.get_role_level(user_role)
        if target_current_level >= user_level:
            raise ForbiddenException(
                f"You cannot modify a course member with role '{target_current_role}'. "
                f"Your role '{user_role}' can only modify members with lower privilege levels."
            )

    # If updating course_role_id, validate role escalation
    if hasattr(entity, 'course_role_id') and entity.course_role_id is not None:
        target_role = entity.course_role_id
        if not course_role_hierarchy.can_assign_role(user_role, target_role):
            raise ForbiddenException(
                f"You cannot assign the role '{target_role}'. "
                f"Your role '{user_role}' can only assign roles at or below your privilege level."
            )

    # Return query for the specific course member
    return db.query(CourseMember)


class CourseMemberInterface(CourseMemberInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseMember interface with model attached."""

    model = CourseMember
    endpoint = "course-members"
    cache_ttl = 300
    post_create = post_create_course_member
    custom_permissions = custom_permissions_course_member

    @staticmethod
    def search(db: Session, query, params: Optional[CourseMemberQuery]):
        """
        Apply search filters to coursemember query.

        Args:
            db: Database session
            query: SQLAlchemy query object
            params: Query parameters

        Returns:
            Filtered query object
        """
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(CourseMember.id == params.id)
        if params.user_id is not None:
            query = query.filter(CourseMember.user_id == params.user_id)
        if params.course_id is not None:
            query = query.filter(CourseMember.course_id == params.course_id)
        if params.course_group_id is not None:
            query = query.filter(CourseMember.course_group_id == params.course_group_id)
        if params.course_role_id is not None:
            query = query.filter(CourseMember.course_role_id == params.course_role_id)

        return query
