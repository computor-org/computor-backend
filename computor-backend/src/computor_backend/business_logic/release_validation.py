"""
Business logic for release validation.

This module provides validation functions to ensure that selected course contents
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


def resolve_course_contents_to_validate(
    course_id: str | UUID,
    db: Session,
    course_content_ids: list[str | UUID] | None = None,
    parent_id: str | UUID | None = None,
    include_descendants: bool = True,
    all_flag: bool = False
) -> list[CourseContent]:
    """
    Resolve which course contents should be validated based on selection criteria.

    Selection priority:
    1. course_content_ids - specific IDs
    2. parent_id + include_descendants - hierarchical selection
    3. all_flag - all submittable contents
    4. Default - no contents (empty list)

    Args:
        course_id: Course ID
        db: Database session
        course_content_ids: Specific content IDs to validate
        parent_id: Parent content ID for hierarchical selection
        include_descendants: Include descendants of parent
        all_flag: Select all submittable contents

    Returns:
        List of CourseContent objects to validate
    """

    # Build base query for submittable course contents
    query = db.query(CourseContent).options(
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
    )

    # Apply content selection filters
    if course_content_ids:
        # Priority 1: Specific content IDs provided
        query = query.filter(CourseContent.id.in_(course_content_ids))
        logger.info(f"[Validation] Selecting {len(course_content_ids)} specific content IDs for course {course_id}")

    elif parent_id:
        # Priority 2: Parent content ID with descendants
        parent = db.query(CourseContent).filter(CourseContent.id == parent_id).first()
        if parent:
            if include_descendants:
                query = query.filter(CourseContent.path.descendant_of(parent.path))
                logger.info(f"[Validation] Selecting descendants of '{parent.path}' for course {course_id}")
            else:
                query = query.filter(CourseContent.id == parent.id)
                logger.info(f"[Validation] Selecting only '{parent.path}' for course {course_id}")
        else:
            logger.warning(f"[Validation] Parent content {parent_id} not found")
            return []

    elif all_flag:
        # Priority 3: All submittable contents
        logger.info(f"[Validation] Selecting ALL submittable contents for course {course_id}")

    else:
        # No selection criteria - return empty list
        logger.info(f"[Validation] No selection criteria provided - nothing to validate")
        return []

    assignments = query.all()
    logger.info(f"[Validation] Resolved {len(assignments)} submittable course contents for validation")

    return assignments


def validate_course_for_release(
    course_id: str | UUID,
    db: Session,
    force_redeploy: bool = False,
    course_content_ids: list[str | UUID] | None = None,
    parent_id: str | UUID | None = None,
    include_descendants: bool = True,
    all_flag: bool = False
) -> tuple[bool, list[ValidationError]]:
    """
    Validate that selected assignments have valid example deployments.

    This function checks that:
    1. Selected submittable course contents (assignments) have CourseContentDeployment records
    2. Deployment status is valid for release (pending, failed, or deployed if force_redeploy)
    3. Referenced ExampleVersion exists in database

    Args:
        course_id: ID of the course to validate
        db: Database session
        force_redeploy: If True, allow re-deployment of already deployed examples
        course_content_ids: Optional list of specific content IDs to validate
        parent_id: Optional parent content ID to validate descendants
        include_descendants: If True, include descendants of parent
        all_flag: If True, validate all submittable contents

    Returns:
        Tuple of (is_valid, validation_errors)
        - is_valid: True if all assignments are valid for release
        - validation_errors: List of ValidationError objects describing issues

    Raises:
        None - Returns validation errors instead of raising exceptions
    """

    logger.info(f"[Validation] Starting release validation for course {course_id}")
    logger.info(f"[Validation] Parameters: force_redeploy={force_redeploy}, "
                f"course_content_ids={'[' + str(len(course_content_ids)) + ' IDs]' if course_content_ids else None}, "
                f"parent_id={parent_id}, include_descendants={include_descendants}, all={all_flag}")

    # Resolve which content to validate
    assignments = resolve_course_contents_to_validate(
        course_id=course_id,
        db=db,
        course_content_ids=course_content_ids,
        parent_id=parent_id,
        include_descendants=include_descendants,
        all_flag=all_flag
    )

    if not assignments:
        logger.warning(f"[Validation] No submittable course contents found for validation in course {course_id}")
        return True, []  # No assignments = nothing to validate

    logger.info(f"[Validation] Validating {len(assignments)} assignments")

    validation_errors = []

    for i, assignment in enumerate(assignments, 1):
        logger.debug(f"[Validation] [{i}/{len(assignments)}] Checking '{assignment.path}' (ID: {assignment.id})")

        # Get deployment for this assignment
        deployment = db.query(CourseContentDeployment).options(
            joinedload(CourseContentDeployment.example_version)
        ).filter(
            CourseContentDeployment.course_content_id == assignment.id
        ).first()

        # Check 1: Deployment exists
        if not deployment:
            error = ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue="No example assigned"
            )
            validation_errors.append(error)
            logger.error(f"[Validation] ❌ '{assignment.path}': No example assigned")
            continue

        # Check 2: Deployment is not unassigned
        if deployment.deployment_status == 'unassigned':
            error = ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue="Example was unassigned"
            )
            validation_errors.append(error)
            logger.error(f"[Validation] ❌ '{assignment.path}': Example was unassigned")
            continue

        # Check 3: Deployment status is valid for release
        valid_statuses = ['pending', 'failed']
        if force_redeploy:
            valid_statuses.append('deployed')

        if deployment.deployment_status not in valid_statuses:
            error = ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue=f"Invalid deployment status: '{deployment.deployment_status}' (expected: {', '.join(valid_statuses)})"
            )
            validation_errors.append(error)
            logger.error(f"[Validation] ❌ '{assignment.path}': Invalid status '{deployment.deployment_status}' "
                        f"(valid: {', '.join(valid_statuses)})")
            continue

        # Check 4: Example version ID is present
        if not deployment.example_version_id:
            error = ValidationError(
                course_content_id=str(assignment.id),
                title=assignment.title or "Untitled",
                path=str(assignment.path),
                issue="No example version assigned"
            )
            validation_errors.append(error)
            logger.error(f"[Validation] ❌ '{assignment.path}': No example version assigned")
            continue

        # Check 5: Example version exists in database
        if not deployment.example_version:
            # Try to fetch it explicitly (in case relationship wasn't loaded)
            example_version = db.query(ExampleVersion).filter(
                ExampleVersion.id == deployment.example_version_id
            ).first()

            if not example_version:
                error = ValidationError(
                    course_content_id=str(assignment.id),
                    title=assignment.title or "Untitled",
                    path=str(assignment.path),
                    issue=f"Example version {deployment.example_version_id} not found in database"
                )
                validation_errors.append(error)
                logger.error(f"[Validation] ❌ '{assignment.path}': Example version {deployment.example_version_id} not found")
                continue

        logger.debug(f"[Validation] ✅ '{assignment.path}': Valid (status: {deployment.deployment_status})")

    is_valid = len(validation_errors) == 0

    if is_valid:
        logger.info(f"[Validation] ✅ SUCCESS: All {len(assignments)} assignments are valid for release")
    else:
        logger.error(f"[Validation] ❌ FAILED: {len(validation_errors)} issues found out of {len(assignments)} assignments")
        logger.error(f"[Validation] Failed assignments:")
        for error in validation_errors:
            logger.error(f"[Validation]   - {error.path}: {error.issue}")

    return is_valid, validation_errors


def validate_course_contents_for_release(
    course_id: str | UUID,
    course_content_ids: list[str | UUID] | None,
    db: Session,
    force_redeploy: bool = False,
    parent_id: str | UUID | None = None,
    include_descendants: bool = True,
    all_flag: bool = False
) -> tuple[bool, list[ValidationError]]:
    """
    Validate specific course contents for release (convenience wrapper).

    This is a wrapper around validate_course_for_release that provides
    backwards compatibility with the old API.

    Args:
        course_id: ID of the course
        course_content_ids: List of specific course content IDs to validate
        db: Database session
        force_redeploy: If True, allow re-deployment of already deployed examples
        parent_id: Optional parent content ID
        include_descendants: Include descendants of parent
        all_flag: Validate all submittable contents

    Returns:
        Tuple of (is_valid, validation_errors)

    Raises:
        None - Returns validation errors instead of raising exceptions
    """

    return validate_course_for_release(
        course_id=course_id,
        db=db,
        force_redeploy=force_redeploy,
        course_content_ids=course_content_ids,
        parent_id=parent_id,
        include_descendants=include_descendants,
        all_flag=all_flag
    )
