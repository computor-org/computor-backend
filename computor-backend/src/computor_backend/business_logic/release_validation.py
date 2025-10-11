"""
Business logic for release validation.

This module provides validation functions to ensure that all course contents
have valid example assignments before allowing system-level Git releases.
"""

import logging
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from computor_backend.model.course import Course, CourseContent, CourseContentType
from computor_backend.model.deployment import CourseContentDeployment
from computor_backend.model.example import ExampleVersion
from computor_types.lecturer_deployments import ValidationError

logger = logging.getLogger(__name__)


def validate_course_for_release(
    course_id: str | UUID,
    db: Session,
    force_redeploy: bool = False
) -> tuple[bool, list[ValidationError]]:
    """
    Validate that all assignments in a course have valid example deployments.

    This function checks that:
    1. All submittable course contents (assignments) have CourseContentDeployment records
    2. Deployment status is valid for release (pending, failed, or deployed if force_redeploy)
    3. Referenced ExampleVersion exists in database

    Args:
        course_id: ID of the course to validate
        db: Database session
        force_redeploy: If True, allow re-deployment of already deployed examples

    Returns:
        Tuple of (is_valid, validation_errors)
        - is_valid: True if all assignments are valid for release
        - validation_errors: List of ValidationError objects describing issues

    Raises:
        None - Returns validation errors instead of raising exceptions
    """

    # Get all submittable course contents (assignments) for the course
    assignments = db.query(CourseContent).options(
        joinedload(CourseContent.course_content_type).joinedload(CourseContentType.course_content_kind)
    ).join(
        CourseContentType,
        CourseContent.course_content_type_id == CourseContentType.id
    ).filter(
        and_(
            CourseContent.course_id == course_id,
            CourseContent.archived_at.is_(None),  # Exclude archived
            CourseContentType.course_content_kind.has(submittable=True)  # Only submittable
        )
    ).all()

    if not assignments:
        logger.warning(f"No submittable course contents found for course {course_id}")
        return True, []  # No assignments = nothing to validate

    logger.info(f"Validating {len(assignments)} assignments for course {course_id}")

    validation_errors = []

    for assignment in assignments:
        # Get deployment for this assignment
        deployment = db.query(CourseContentDeployment).options(
            joinedload(CourseContentDeployment.example_version)
        ).filter(
            CourseContentDeployment.course_content_id == assignment.id
        ).first()

        # Check 1: Deployment exists
        if not deployment:
            validation_errors.append(ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue="No example assigned"
            ))
            continue

        # Check 2: Deployment is not unassigned
        if deployment.deployment_status == 'unassigned':
            validation_errors.append(ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue="Example was unassigned"
            ))
            continue

        # Check 3: Deployment status is valid for release
        valid_statuses = ['pending', 'failed']
        if force_redeploy:
            valid_statuses.append('deployed')

        if deployment.deployment_status not in valid_statuses:
            validation_errors.append(ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue=f"Invalid deployment status: {deployment.deployment_status}"
            ))
            continue

        # Check 4: Example version ID is present
        if not deployment.example_version_id:
            validation_errors.append(ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue="No example version assigned"
            ))
            continue

        # Check 5: Example version exists in database
        if not deployment.example_version:
            # Try to fetch it explicitly (in case relationship wasn't loaded)
            example_version = db.query(ExampleVersion).filter(
                ExampleVersion.id == deployment.example_version_id
            ).first()

            if not example_version:
                validation_errors.append(ValidationError(
                    course_content_id=str(assignment.id),
                    title=assignment.title or "Untitled",
                    path=str(assignment.path),
                    issue=f"Example version {deployment.example_version_id} not found in database"
                ))
                continue

    is_valid = len(validation_errors) == 0

    if is_valid:
        logger.info(f"Course {course_id} passed validation: all {len(assignments)} assignments are valid")
    else:
        logger.warning(
            f"Course {course_id} failed validation: {len(validation_errors)} issues found "
            f"out of {len(assignments)} assignments"
        )

    return is_valid, validation_errors


def validate_course_contents_for_release(
    course_id: str | UUID,
    course_content_ids: list[str | UUID] | None,
    db: Session,
    force_redeploy: bool = False
) -> tuple[bool, list[ValidationError]]:
    """
    Validate specific course contents for release.

    Similar to validate_course_for_release but only validates the specified
    course contents instead of all assignments in the course.

    Args:
        course_id: ID of the course
        course_content_ids: List of specific course content IDs to validate (None = all)
        db: Database session
        force_redeploy: If True, allow re-deployment of already deployed examples

    Returns:
        Tuple of (is_valid, validation_errors)

    Raises:
        None - Returns validation errors instead of raising exceptions
    """

    # If no specific IDs provided, validate entire course
    if not course_content_ids:
        return validate_course_for_release(course_id, db, force_redeploy)

    # Get specified course contents
    assignments = db.query(CourseContent).options(
        joinedload(CourseContent.course_content_type).joinedload(CourseContentType.course_content_kind)
    ).join(
        CourseContentType,
        CourseContent.course_content_type_id == CourseContentType.id
    ).filter(
        and_(
            CourseContent.id.in_(course_content_ids),
            CourseContent.course_id == course_id,
            CourseContent.archived_at.is_(None),
            CourseContentType.course_content_kind.has(submittable=True)
        )
    ).all()

    if not assignments:
        logger.warning(f"No valid submittable course contents found from provided IDs for course {course_id}")
        return True, []

    logger.info(f"Validating {len(assignments)} specific assignments for course {course_id}")

    validation_errors = []

    for assignment in assignments:
        # Get deployment for this assignment
        deployment = db.query(CourseContentDeployment).options(
            joinedload(CourseContentDeployment.example_version)
        ).filter(
            CourseContentDeployment.course_content_id == assignment.id
        ).first()

        # Check 1: Deployment exists
        if not deployment:
            validation_errors.append(ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue="No example assigned"
            ))
            continue

        # Check 2: Deployment is not unassigned
        if deployment.deployment_status == 'unassigned':
            validation_errors.append(ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue="Example was unassigned"
            ))
            continue

        # Check 3: Deployment status is valid for release
        valid_statuses = ['pending', 'failed']
        if force_redeploy:
            valid_statuses.append('deployed')

        if deployment.deployment_status not in valid_statuses:
            validation_errors.append(ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue=f"Invalid deployment status: {deployment.deployment_status}"
            ))
            continue

        # Check 4: Example version ID is present
        if not deployment.example_version_id:
            validation_errors.append(ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue="No example version assigned"
            ))
            continue

        # Check 5: Example version exists in database
        if not deployment.example_version:
            # Try to fetch it explicitly
            example_version = db.query(ExampleVersion).filter(
                ExampleVersion.id == deployment.example_version_id
            ).first()

            if not example_version:
                validation_errors.append(ValidationError(
                    course_content_id=str(assignment.id),
                    title=assignment.title or "Untitled",
                    path=str(assignment.path),
                    issue=f"Example version {deployment.example_version_id} not found in database"
                ))
                continue

    is_valid = len(validation_errors) == 0

    if is_valid:
        logger.info(f"Validation passed: all {len(assignments)} specified assignments are valid")
    else:
        logger.warning(
            f"Validation failed: {len(validation_errors)} issues found "
            f"out of {len(assignments)} specified assignments"
        )

    return is_valid, validation_errors
