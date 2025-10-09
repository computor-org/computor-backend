"""
Submission group provisioning - ensures submission groups exist for students.

This module provides functions to automatically create submission groups
for students when they access submittable course content.
"""

import logging
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from computor_backend.model.course import (
    CourseContent,
    CourseMember,
    CourseContentKind,
    SubmissionGroup,
    SubmissionGroupMember,
)
from computor_backend.api.exceptions import NotImplementedException

logger = logging.getLogger(__name__)


def provision_submission_groups_for_user(
    user_id: UUID | str,
    course_id: UUID | str | None,
    db: Session
) -> None:
    """
    Provision submission groups for a user's submittable course contents.

    Creates individual submission groups (max_group_size None or 1) for all
    submittable course contents where the user doesn't have a submission group yet.

    Team assignments (max_group_size > 1) are skipped - these require manual creation
    through instructor actions or student team formation workflow.

    Args:
        user_id: User ID
        course_id: Optional course ID to limit provisioning to specific course
        db: Database session
    """
    # Get all course members for this user with user info loaded
    from sqlalchemy.orm import joinedload
    course_members_query = db.query(CourseMember).options(
        joinedload(CourseMember.user)
    ).filter(
        CourseMember.user_id == user_id
    )
    if course_id:
        course_members_query = course_members_query.filter(CourseMember.course_id == course_id)

    course_members = course_members_query.all()

    if not course_members:
        return

    for course_member in course_members:
        # Get all submittable course contents for this course
        submittable_contents = (
            db.query(CourseContent, CourseContentKind)
            .join(CourseContentKind, CourseContentKind.id == CourseContent.course_content_kind_id)
            .filter(
                CourseContent.course_id == course_member.course_id,
                CourseContentKind.submittable == True
            )
            .all()
        )

        for course_content, course_content_kind in submittable_contents:
            # Check max_group_size
            if course_content.max_group_size is not None and course_content.max_group_size > 1:
                # Skip team submissions - these require manual creation or student self-organization
                logger.info(
                    f"Skipping automatic submission group creation for team assignment "
                    f"'{course_content.title}' (max_group_size={course_content.max_group_size}). "
                    f"Teams must be created manually or through team formation workflow."
                )
                continue

            # Check if submission group already exists for this member and content
            existing_group = (
                db.query(SubmissionGroup)
                .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
                .filter(
                    SubmissionGroup.course_content_id == course_content.id,
                    SubmissionGroupMember.course_member_id == course_member.id
                )
                .first()
            )

            if existing_group:
                continue  # Already exists

            # Create submission group for individual submission
            logger.info(
                f"Provisioning submission group for user {user_id}, "
                f"member {course_member.id}, content {course_content.id}"
            )

            # Generate display name for individual submission (max_group_size == 1 or None)
            display_name = None
            max_group_size = course_content.max_group_size if course_content.max_group_size is not None else 1
            if max_group_size == 1 and course_member.user:
                given_name = course_member.user.given_name or ""
                family_name = course_member.user.family_name or ""
                display_name = f"{given_name} {family_name}".strip()
                if not display_name:
                    display_name = course_member.user.email

            submission_group = SubmissionGroup(
                course_content_id=course_content.id,
                course_id=course_member.course_id,
                max_group_size=max_group_size,
                max_test_runs=course_content.max_test_runs,
                display_name=display_name,
                properties={}
            )
            db.add(submission_group)
            db.flush()  # Get the ID

            # Create submission group member
            submission_group_member = SubmissionGroupMember(
                submission_group_id=submission_group.id,
                course_member_id=course_member.id,
                course_id=course_member.course_id
            )
            db.add(submission_group_member)

    # Commit all changes at once
    db.commit()
    logger.info(f"Finished provisioning submission groups for user {user_id}")
