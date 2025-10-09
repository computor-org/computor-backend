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

    Creates submission groups for all submittable course contents with max_group_size=1 or None,
    and triggers the StudentRepositoryCreationWorkflow to create GitLab repository.

    Args:
        course_member: The newly created course member
        db: Database session
    """
    # Only process for actual users (not system accounts)
    if course_member.user.user_type != "user":
        logger.info(f"Skipping post_create for non-user course member {course_member.id}")
        return

    logger.info(f"Running post_create for course member {course_member.id} (user: {course_member.user_id}, course: {course_member.course_id})")

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
