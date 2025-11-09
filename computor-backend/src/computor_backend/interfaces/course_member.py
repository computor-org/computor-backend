"""Backend CourseMember interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session
import logging

from computor_types.course_members import (
    CourseMemberInterface as CourseMemberInterfaceBase,
    CourseMemberQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseMember, SubmissionGroup, SubmissionGroupMember

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

    # Trigger StudentRepositoryCreationWorkflow
    try:
        from computor_backend.tasks import get_task_executor
        from computor_types.tasks import TaskSubmission

        task_executor = get_task_executor()

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

        workflow_id = await task_executor.submit_task(task_submission)
        logger.info(f"Triggered StudentRepositoryCreationWorkflow: {workflow_id} for course member {course_member.id}")
    except Exception as e:
        logger.error(f"Failed to trigger StudentRepositoryCreationWorkflow for course member {course_member.id}: {e}")
        # Don't fail the course member creation if workflow submission fails


class CourseMemberInterface(CourseMemberInterfaceBase, BackendEntityInterface):
    """Backend-specific CourseMember interface with model attached."""

    model = CourseMember
    endpoint = "course-members"
    cache_ttl = 300
    post_create = post_create_course_member

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
