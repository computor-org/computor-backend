"""Business logic for submission group management."""

import logging
from uuid import UUID
from sqlalchemy.orm import Session

from computor_backend.model.course import (
    CourseContent,
    CourseMember,
    SubmissionGroup,
    SubmissionGroupMember,
    CourseContentKind,
)
from computor_backend.api.exceptions import NotImplementedException

logger = logging.getLogger(__name__)


def ensure_submission_group_exists(
    course_member_id: UUID | str,
    course_content_id: UUID | str,
    db: Session
) -> SubmissionGroup | None:
    """
    Ensure a submission group exists for a course member and course content.

    Creates submission group lazily when:
    - Course content is submittable (course_content_kind.submittable = True)
    - max_group_size is None or 1 (individual submissions)

    Team assignments (max_group_size > 1) are not auto-created - these require
    manual creation through instructor actions or student team formation workflow.

    Args:
        course_member_id: ID of the course member
        course_content_id: ID of the course content
        db: Database session

    Returns:
        SubmissionGroup if content is submittable and group was created/found, None otherwise
        Returns None for team assignments (max_group_size > 1) that haven't been created yet
    """
    # Get course content with related data
    course_content = db.query(CourseContent).filter(
        CourseContent.id == course_content_id
    ).first()

    if not course_content:
        return None

    # Check if content is submittable
    course_content_kind = db.query(CourseContentKind).filter(
        CourseContentKind.id == course_content.course_content_kind_id
    ).first()

    if not course_content_kind or not course_content_kind.submittable:
        # Not submittable, no submission group needed
        return None

    # Check max_group_size
    max_group_size = course_content.max_group_size

    # Check if submission group already exists for this member and content
    existing_group = (
        db.query(SubmissionGroup)
        .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
        .filter(
            SubmissionGroup.course_content_id == course_content_id,
            SubmissionGroupMember.course_member_id == course_member_id
        )
        .first()
    )

    if existing_group:
        logger.debug(
            f"Submission group {existing_group.id} already exists for "
            f"member {course_member_id} and content {course_content_id}"
        )
        return existing_group

    # For team assignments, don't auto-create - return None
    if max_group_size is not None and max_group_size > 1:
        logger.info(
            f"Team assignment '{course_content.title}' (max_group_size={max_group_size}) has no team "
            f"for student {course_member_id}. Team must be created through team formation workflow."
        )
        return None

    # Create new submission group for individual submission
    logger.info(
        f"Creating submission group for member {course_member_id} "
        f"and content {course_content_id} (individual submission)"
    )

    # Get course member to access course_id and user info
    from sqlalchemy.orm import joinedload
    course_member = db.query(CourseMember).options(
        joinedload(CourseMember.user)
    ).filter(
        CourseMember.id == course_member_id
    ).first()

    if not course_member:
        return None

    # Generate display name for individual submission
    display_name = None
    if course_member.user:
        given_name = course_member.user.given_name or ""
        family_name = course_member.user.family_name or ""
        display_name = f"{given_name} {family_name}".strip()
        if not display_name:
            display_name = course_member.user.email

    # Create submission group
    submission_group = SubmissionGroup(
        course_content_id=course_content_id,
        course_id=course_member.course_id,
        max_test_runs=course_content.max_test_runs,
        display_name=display_name,
        properties={}
    )
    db.add(submission_group)
    db.flush()  # Get the ID

    # Create submission group member
    submission_group_member = SubmissionGroupMember(
        submission_group_id=submission_group.id,
        course_member_id=course_member_id
    )
    db.add(submission_group_member)
    db.commit()

    logger.info(
        f"Created submission group {submission_group.id} with member {course_member_id}"
    )

    return submission_group
