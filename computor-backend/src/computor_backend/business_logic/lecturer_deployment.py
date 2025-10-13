"""
Business logic for lecturer deployment operations.

This module handles the assignment of examples to course contents (phase 1),
separate from the system-level Git release operations (phase 2).
"""

import logging
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from computor_backend.model.course import Course, CourseContent, CourseContentType
from computor_backend.model.deployment import CourseContentDeployment, DeploymentHistory
from computor_backend.model.example import Example, ExampleVersion
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.api.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException
)
from computor_types.validation import SemanticVersion
from computor_types.custom_types import Ltree

logger = logging.getLogger(__name__)


def validate_semantic_version(version_str: str) -> SemanticVersion:
    """
    Validate version string follows semantic versioning.

    Args:
        version_str: Version string to validate

    Returns:
        SemanticVersion instance

    Raises:
        BadRequestException: If version format is invalid
    """
    try:
        return SemanticVersion.from_string(version_str)
    except ValueError as e:
        raise BadRequestException(str(e))


def assign_example_to_content(
    course_content_id: str | UUID,
    example_id: str | UUID,
    version_tag: str,
    permissions: Principal,
    db: Session
) -> CourseContentDeployment:
    """
    Assign an example version to a course content (assignment).

    This is phase 1: Database-only assignment, no Git operations.

    Args:
        course_content_id: ID of the course content (must be submittable)
        example_id: ID of the example to assign
        version_tag: Semantic version tag (e.g., "1.0.0", "2.1.3-beta")
        permissions: Current user's permissions
        db: Database session

    Returns:
        CourseContentDeployment record

    Raises:
        NotFoundException: If resources don't exist
        ForbiddenException: If user lacks permissions
        BadRequestException: If validation fails
    """

    # 1. Validate version format
    validate_semantic_version(version_tag)

    # 2. Get and validate course content with relationships
    course_content = db.query(CourseContent).options(
        joinedload(CourseContent.course),
        joinedload(CourseContent.course_content_type).joinedload(CourseContentType.course_content_kind)
    ).filter(CourseContent.id == course_content_id).first()

    if not course_content:
        raise NotFoundException(f"Course content {course_content_id} not found")

    # 3. Check permissions (lecturer or higher)
    course_query = check_course_permissions(
        permissions,
        Course,
        "_lecturer",
        db
    )
    course = course_query.filter(Course.id == course_content.course_id).first()

    if not course:
        raise ForbiddenException(
            "You don't have permission to assign examples to this course"
        )

    # 4. Validate course content is submittable (assignment)
    content_type = course_content.course_content_type
    if not content_type or not content_type.course_content_kind:
        raise BadRequestException(
            f"Course content {course_content_id} has no content type or kind"
        )

    if not content_type.course_content_kind.submittable:
        raise BadRequestException(
            f"Cannot assign examples to non-submittable content. "
            f"Content kind '{content_type.course_content_kind.id}' is not submittable."
        )

    # 5. Validate example exists
    example = db.query(Example).filter(Example.id == example_id).first()
    if not example:
        raise NotFoundException(f"Example {example_id} not found")

    # 6. Find specific version
    example_version = db.query(ExampleVersion).filter(
        and_(
            ExampleVersion.example_id == example_id,
            ExampleVersion.version_tag == version_tag
        )
    ).first()

    if not example_version:
        raise NotFoundException(
            f"Example version '{version_tag}' not found for example {example_id}"
        )

    # 7. Check if deployment already exists
    existing_deployment = db.query(CourseContentDeployment).filter(
        CourseContentDeployment.course_content_id == course_content_id
    ).first()

    if existing_deployment:
        # Update existing deployment (only if not already deployed)
        if existing_deployment.deployment_status == 'deployed':
            raise BadRequestException(
                f"Cannot reassign: Example already deployed. "
                f"Current deployment status: {existing_deployment.deployment_status}"
            )

        # Track previous version for history
        previous_version_id = existing_deployment.example_version_id

        # Update deployment
        existing_deployment.example_version_id = example_version.id
        existing_deployment.example_identifier = example.identifier
        existing_deployment.version_tag = version_tag
        existing_deployment.deployment_status = 'pending'
        existing_deployment.assigned_at = datetime.now(timezone.utc)
        existing_deployment.deployment_message = None
        existing_deployment.updated_by = permissions.user_id

        # Create history entry
        history = DeploymentHistory(
            deployment_id=existing_deployment.id,
            action='reassigned',
            example_version_id=example_version.id,
            previous_example_version_id=previous_version_id,
            example_identifier=example.identifier,
            version_tag=version_tag,
            created_by=permissions.user_id
        )
        db.add(history)

        db.commit()
        db.refresh(existing_deployment)

        logger.info(
            f"Reassigned example {example_id} (v{version_tag}) to content {course_content_id}"
        )

        return existing_deployment

    else:
        # Create new deployment
        deployment = CourseContentDeployment(
            course_content_id=course_content_id,
            example_version_id=example_version.id,
            example_identifier=example.identifier,
            version_tag=version_tag,
            deployment_status='pending',
            assigned_at=datetime.now(timezone.utc),
            created_by=permissions.user_id,
            updated_by=permissions.user_id
        )
        db.add(deployment)
        db.flush()  # Get deployment ID

        # Create history entry
        history = DeploymentHistory(
            deployment_id=deployment.id,
            action='assigned',
            example_version_id=example_version.id,
            example_identifier=example.identifier,
            version_tag=version_tag,
            created_by=permissions.user_id
        )
        db.add(history)

        db.commit()
        db.refresh(deployment)

        logger.info(
            f"Assigned example {example_id} (v{version_tag}) to content {course_content_id}"
        )

        return deployment


def get_deployment_for_content(
    course_content_id: str | UUID,
    permissions: Principal,
    db: Session
) -> CourseContentDeployment | None:
    """
    Get deployment information for a course content.

    Args:
        course_content_id: ID of the course content
        permissions: Current user's permissions
        db: Database session

    Returns:
        CourseContentDeployment or None if no deployment exists

    Raises:
        NotFoundException: If course content doesn't exist
        ForbiddenException: If user lacks permissions
    """

    # Get course content with relationships
    course_content = db.query(CourseContent).options(
        joinedload(CourseContent.course)
    ).filter(CourseContent.id == course_content_id).first()

    if not course_content:
        raise NotFoundException(f"Course content {course_content_id} not found")

    # Check permissions (lecturer or higher)
    course_query = check_course_permissions(
        permissions,
        Course,
        "_lecturer",
        db
    )
    course = course_query.filter(Course.id == course_content.course_id).first()

    if not course:
        raise ForbiddenException(
            "You don't have permission to view deployments for this course"
        )

    # Get deployment with relationships
    deployment = db.query(CourseContentDeployment).options(
        joinedload(CourseContentDeployment.example_version).joinedload(ExampleVersion.example),
        joinedload(CourseContentDeployment.course_content)
    ).filter(
        CourseContentDeployment.course_content_id == course_content_id
    ).first()

    return deployment


def unassign_example_from_content(
    course_content_id: str | UUID,
    permissions: Principal,
    db: Session
) -> dict:
    """
    Unassign an example from a course content (only if not deployed).

    Args:
        course_content_id: ID of the course content
        permissions: Current user's permissions
        db: Database session

    Returns:
        Dictionary with unassignment details

    Raises:
        NotFoundException: If resources don't exist
        ForbiddenException: If user lacks permissions
        BadRequestException: If already deployed
    """

    # Get course content with relationships
    course_content = db.query(CourseContent).options(
        joinedload(CourseContent.course)
    ).filter(CourseContent.id == course_content_id).first()

    if not course_content:
        raise NotFoundException(f"Course content {course_content_id} not found")

    # Check permissions (lecturer or higher)
    course_query = check_course_permissions(
        permissions,
        Course,
        "_lecturer",
        db
    )
    course = course_query.filter(Course.id == course_content.course_id).first()

    if not course:
        raise ForbiddenException(
            "You don't have permission to unassign examples from this course"
        )

    # Get deployment
    deployment = db.query(CourseContentDeployment).filter(
        CourseContentDeployment.course_content_id == course_content_id
    ).first()

    if not deployment:
        raise NotFoundException(
            f"No example assigned to course content {course_content_id}"
        )

    # Check if already deployed
    if deployment.deployment_status in ('deployed', 'deploying'):
        raise BadRequestException(
            f"Cannot unassign: Example is already deployed or being deployed. "
            f"Current status: {deployment.deployment_status}"
        )

    # Store info for response
    previous_example_id = deployment.example_version_id
    previous_version_tag = deployment.version_tag

    # Create history entry before marking as unassigned
    history = DeploymentHistory(
        deployment_id=deployment.id,
        action='unassigned',
        example_version_id=deployment.example_version_id,
        example_identifier=deployment.example_identifier,
        version_tag=deployment.version_tag,
        created_by=permissions.user_id
    )
    db.add(history)

    # Mark as unassigned (don't delete, keep history)
    deployment.deployment_status = 'unassigned'
    deployment.example_version_id = None
    deployment.deployment_message = 'Unassigned by lecturer'
    deployment.updated_by = permissions.user_id

    db.commit()

    logger.info(f"Unassigned example from content {course_content_id}")

    return {
        'course_content_id': str(course_content_id),
        'previous_example_id': str(previous_example_id) if previous_example_id else None,
        'previous_version_tag': previous_version_tag,
        'message': 'Example successfully unassigned from course content'
    }


def batch_validate_content(
    course_id: str | UUID,
    content_validations: list[dict],
    permissions: Principal,
    db: Session
) -> dict:
    """
    Batch validate multiple course contents with their assigned examples and versions.

    This optimizes validation from N×2 HTTP requests to a single request by:
    1. Batch fetching all examples by identifier
    2. Batch fetching all versions for found examples
    3. Building lookup maps for O(1) validation

    Args:
        course_id: ID of the course
        content_validations: List of dicts with content_id, content_path, example_identifier, version_tag
        permissions: Current user's permissions
        db: Database session

    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "total_validated": int,
            "total_issues": int,
            "validation_results": [...]
        }

    Raises:
        ForbiddenException: If user lacks permissions
        NotFoundException: If course doesn't exist
    """

    # 1. Check permissions (lecturer or higher)
    course_query = check_course_permissions(
        permissions,
        Course,
        "_lecturer",
        db
    )
    course = course_query.filter(Course.id == course_id).first()

    if not course:
        raise ForbiddenException(
            "You don't have permission to validate content for this course"
        )

    # 2. Extract all unique example identifiers and build content map
    identifiers = set()
    content_map = {}  # content_id -> validation_item

    for item in content_validations:
        identifiers.add(item['example_identifier'])
        content_map[item['content_id']] = item

    # 3. Batch fetch all examples by identifier
    # Convert string identifiers to Ltree objects for proper SQLAlchemy comparison
    ltree_identifiers = [Ltree(identifier) for identifier in identifiers]

    examples = db.query(Example).filter(
        Example.identifier.in_(ltree_identifiers)
    ).all()

    # Build example lookup map: identifier -> example
    example_map = {str(ex.identifier): ex for ex in examples}

    # 4. Get all example IDs for version lookup
    example_ids = [ex.id for ex in examples]

    # 5. Batch fetch all versions for these examples
    versions = db.query(ExampleVersion).filter(
        ExampleVersion.example_id.in_(example_ids)
    ).all()

    # Build version lookup map: (example_id, version_tag) -> version
    version_map = {}
    for version in versions:
        key = (str(version.example_id), version.version_tag)
        version_map[key] = version

    # 6. Validate each content item
    validation_results = []
    total_issues = 0

    for item in content_validations:
        content_id = item['content_id']
        example_identifier = item['example_identifier']
        version_tag = item['version_tag']

        # Validate example exists
        example = example_map.get(example_identifier)

        if example:
            example_validation = {
                'identifier': example_identifier,
                'exists': True,
                'example_id': str(example.id),
                'message': None
            }
        else:
            example_validation = {
                'identifier': example_identifier,
                'exists': False,
                'example_id': None,
                'message': f"Example '{example_identifier}' not found"
            }

        # Validate version exists (only if example exists)
        if example:
            version_key = (str(example.id), version_tag)
            version = version_map.get(version_key)

            if version:
                version_validation = {
                    'version_tag': version_tag,
                    'exists': True,
                    'version_id': str(version.id),
                    'message': None
                }
            else:
                version_validation = {
                    'version_tag': version_tag,
                    'exists': False,
                    'version_id': None,
                    'message': f"Version '{version_tag}' not found for example '{example_identifier}'"
                }
        else:
            # Can't check version if example doesn't exist
            version_validation = {
                'version_tag': version_tag,
                'exists': False,
                'version_id': None,
                'message': 'Cannot validate version - example does not exist'
            }

        # Determine overall validity
        is_valid = example_validation['exists'] and version_validation['exists']

        if not is_valid:
            total_issues += 1

        # Build validation message
        validation_message = None
        if not is_valid:
            messages = []
            if not example_validation['exists']:
                messages.append(example_validation['message'])
            if not version_validation['exists']:
                messages.append(version_validation['message'])
            validation_message = '; '.join(messages)

        # Add result
        validation_results.append({
            'content_id': content_id,
            'valid': is_valid,
            'example_validation': example_validation,
            'version_validation': version_validation,
            'validation_message': validation_message
        })

    # 7. Build response
    overall_valid = total_issues == 0

    logger.info(
        f"Batch validation for course {course_id}: "
        f"{len(content_validations)} items validated, "
        f"{total_issues} issues found"
    )

    return {
        'valid': overall_valid,
        'total_validated': len(content_validations),
        'total_issues': total_issues,
        'validation_results': validation_results
    }
