"""
Submission group provisioning - ensures submission groups exist for students.

This module provides functions to automatically create submission groups
for students when they access submittable course content.
"""

import logging
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
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


def _create_submission_group_for_member(
    course_member: CourseMember,
    course_content: CourseContent,
    db: Session
) -> SubmissionGroup | None:
    """
    Helper function to create or update a submission group for a course member and course content.

    For individual assignments (max_group_size=1 or None), copies GitLab repository
    information from course_member.properties['gitlab'] to submission_group.properties['gitlab'].

    If submission group already exists but has empty GitLab properties, it will be updated.

    For team assignments, properties remain empty (team repos are created separately).

    Args:
        course_member: CourseMember with user relationship loaded
        course_content: CourseContent to create submission group for
        db: Database session

    Returns:
        Created or updated SubmissionGroup, or None if already exists and properly configured
    """
    # Check if submission group already exists
    existing_group = (
        db.query(SubmissionGroup)
        .join(SubmissionGroupMember, SubmissionGroupMember.submission_group_id == SubmissionGroup.id)
        .filter(
            SubmissionGroup.course_content_id == course_content.id,
            SubmissionGroupMember.course_member_id == course_member.id
        )
        .first()
    )

    # Calculate max_group_size
    max_group_size = course_content.max_group_size if course_content.max_group_size is not None else 1

    # If group exists, check if it needs GitLab properties update
    if existing_group:
        # Only update if it's an individual assignment AND GitLab properties are missing
        needs_update = (
            max_group_size == 1 and
            course_member.properties and
            'gitlab' in course_member.properties and
            (not existing_group.properties or 'gitlab' not in existing_group.properties)
        )

        if needs_update:
            # Update existing group with GitLab info
            from sqlalchemy.orm.attributes import flag_modified

            gitlab_info = course_member.properties['gitlab'].copy()

            # Add assignment-specific directory if available
            assignment_directory = None
            if course_content.deployment and course_content.deployment.example_version:
                example = course_content.deployment.example_version.example
                if example and example.directory:
                    assignment_directory = example.directory

            # Fallback to course content path
            if not assignment_directory and course_content.path:
                assignment_directory = str(course_content.path)

            if assignment_directory:
                gitlab_info['directory'] = assignment_directory

            # Update properties
            if not existing_group.properties:
                existing_group.properties = {}
            existing_group.properties['gitlab'] = gitlab_info
            flag_modified(existing_group, "properties")
            db.add(existing_group)

            logger.info(
                f"Updated submission group {existing_group.id} with GitLab properties "
                f"for member {course_member.id}, content {course_content.id}"
            )
            return existing_group
        else:
            # Already exists and properly configured, or is a team assignment
            return None

    # Generate display name for individual submission (max_group_size == 1 or None)
    display_name = None
    if max_group_size == 1 and course_member.user:
        given_name = course_member.user.given_name or ""
        family_name = course_member.user.family_name or ""
        display_name = f"{given_name} {family_name}".strip()
        if not display_name:
            display_name = course_member.user.email

    # Prepare properties - for individual assignments, copy GitLab info from course_member
    properties = {}
    if max_group_size == 1 and course_member.properties and 'gitlab' in course_member.properties:
        # This is an individual assignment - copy the student's GitLab repository info
        gitlab_info = course_member.properties['gitlab'].copy()

        # Add assignment-specific directory if available
        assignment_directory = None
        if course_content.deployment and course_content.deployment.example_version:
            example = course_content.deployment.example_version.example
            if example and example.directory:
                assignment_directory = example.directory

        # Fallback to course content path
        if not assignment_directory and course_content.path:
            assignment_directory = str(course_content.path)

        if assignment_directory:
            gitlab_info['directory'] = assignment_directory

        properties['gitlab'] = gitlab_info
        logger.debug(
            f"Preparing GitLab repository info from course_member {course_member.id} "
            f"for new submission group, content {course_content.id}"
        )
    # For team assignments (max_group_size > 1), properties remain empty {}
    # Team repositories will be created separately through team formation workflow

    # Create submission group
    submission_group = SubmissionGroup(
        course_content_id=course_content.id,
        course_id=course_member.course_id,
        max_group_size=max_group_size,
        max_test_runs=course_content.max_test_runs,
        max_submissions=course_content.max_submissions,
        display_name=display_name,
        properties=properties
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

    logger.info(
        f"Created submission group {submission_group.id} for "
        f"member {course_member.id}, content {course_content.id}"
    )

    return submission_group


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

    created_count = 0
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
            # Check max_group_size - skip team assignments
            if course_content.max_group_size is not None and course_content.max_group_size > 1:
                logger.debug(
                    f"Skipping team assignment '{course_content.title}' "
                    f"(max_group_size={course_content.max_group_size})"
                )
                continue

            # Use helper function to create submission group
            submission_group = _create_submission_group_for_member(
                course_member, course_content, db
            )
            if submission_group:
                created_count += 1

    # Commit all changes at once
    db.commit()
    logger.info(
        f"Provisioned {created_count} submission groups for user {user_id}"
    )


def provision_submission_groups_for_course_content(
    course_content_id: UUID | str,
    db: Session
) -> int:
    """
    Provision submission groups for all students when a new course content is created.

    Creates individual submission groups (max_group_size None or 1) for all
    enrolled students in the course.

    Team assignments (max_group_size > 1) are skipped - these require manual creation
    through instructor actions or student team formation workflow.

    Args:
        course_content_id: ID of the newly created course content
        db: Database session

    Returns:
        Number of submission groups created
    """
    # Get course content with kind
    course_content_query = (
        db.query(CourseContent, CourseContentKind)
        .join(CourseContentKind, CourseContentKind.id == CourseContent.course_content_kind_id)
        .filter(CourseContent.id == course_content_id)
    )

    result = course_content_query.first()
    if not result:
        logger.warning(f"CourseContent {course_content_id} not found")
        return 0

    course_content, course_content_kind = result

    # Check if content is submittable
    if not course_content_kind.submittable:
        logger.debug(
            f"CourseContent {course_content_id} is not submittable, "
            "skipping submission group provisioning"
        )
        return 0

    # Check max_group_size - skip team assignments
    if course_content.max_group_size is not None and course_content.max_group_size > 1:
        logger.info(
            f"CourseContent {course_content_id} is a team assignment "
            f"(max_group_size={course_content.max_group_size}). "
            "Submission groups will be created through team formation workflow."
        )
        return 0

    # Get all students enrolled in this course
    course_members = db.query(CourseMember).options(
        joinedload(CourseMember.user)
    ).filter(
        CourseMember.course_id == course_content.course_id,
        CourseMember.course_role_id == '_student'
    ).all()

    if not course_members:
        logger.info(
            f"No students enrolled in course {course_content.course_id}, "
            "skipping submission group provisioning"
        )
        return 0

    # Create submission groups for each student
    created_count = 0
    for course_member in course_members:
        submission_group = _create_submission_group_for_member(
            course_member, course_content, db
        )
        if submission_group:
            created_count += 1

    # Commit all changes at once
    db.commit()
    logger.info(
        f"Provisioned {created_count} submission groups for "
        f"CourseContent {course_content_id} ({course_content.title})"
    )

    return created_count
