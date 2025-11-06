"""
Business logic for lecturer deployment operations.

This module handles the assignment of examples to course contents (phase 1),
separate from the system-level Git release operations (phase 2).
"""

import logging
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from computor_backend.model.course import Course, CourseContent, CourseContentType
from computor_backend.model.deployment import CourseContentDeployment, DeploymentHistory
from computor_backend.model.example import Example, ExampleVersion
from computor_backend.permissions.principal import Principal
from computor_backend.permissions.core import check_course_permissions
from computor_backend.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException
)
from computor_backend.custom_types.ltree import Ltree
from computor_types.validation import SemanticVersion, normalize_version

logger = logging.getLogger(__name__)


def validate_reassignment_allowed(
    existing_deployment: CourseContentDeployment,
    new_example_identifier: str,
    course_content_id: str
) -> tuple[bool, str]:
    """
    Validate if reassignment is allowed based on deployment status and example identity.

    Rules:
    - If not deployed: Allow any reassignment
    - If deployed + same example: Allow (version update)
    - If deployed + different example: Reject

    Args:
        existing_deployment: Current deployment record
        new_example_identifier: Identifier of new example being assigned
        course_content_id: ID of the course content (for error context)

    Returns:
        Tuple of (is_same_example, action_type)
        - is_same_example: Whether this is updating the same example
        - action_type: 'updated', 'reassigned', or 'assigned'

    Raises:
        BadRequestException: If deployed and trying to assign different example
    """
    current_identifier = existing_deployment.example_identifier
    is_same_example = str(current_identifier) == str(new_example_identifier)

    # If deployed, only allow reassignment if it's the same example (version update)
    if existing_deployment.deployment_status == 'deployed' and not is_same_example:
        raise BadRequestException(
            error_code="DEPLOY_001",
            detail="Cannot reassign to different example: Current example is already deployed. "
                   "Reassignment to a different version of the same example is allowed.",
            context={
                "course_content_id": str(course_content_id),
                "current_status": existing_deployment.deployment_status,
                "current_example": str(current_identifier) if current_identifier else None,
                "new_example": str(new_example_identifier),
                "is_same_example": is_same_example
            }
        )

    # Determine action type for history
    if is_same_example:
        action = 'updated' if existing_deployment.deployment_status == 'deployed' else 'reassigned'
    else:
        action = 'reassigned'

    return is_same_example, action


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
        raise BadRequestException(
            error_code="VAL_003",
            detail=str(e),
            context={"version_string": version_str}
        )


def assign_example_to_content(
    course_content_id: str | UUID,
    example_id: str | UUID | None = None,
    version_tag: str = "",
    permissions: Principal = None,
    db: Session = None,
    example_identifier: str | None = None
) -> CourseContentDeployment:
    """
    Assign an example version to a course content (assignment).

    This is phase 1: Database-only assignment, no Git operations.

    Args:
        course_content_id: ID of the course content (must be submittable)
        example_id: ID of the example to assign (UUID) - optional if example_identifier provided
        example_identifier: Identifier path of the example (e.g., 'itpcp.pgph.mat.example') - optional if example_id provided
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

    # 0. Validate that either example_id or example_identifier is provided
    if not example_id and not example_identifier:
        raise BadRequestException(
            error_code="VAL_002",
            detail="Either example_id or example_identifier must be provided",
            context={}
        )

    # 1. Normalize and validate version format
    # Normalize short versions like '1.2' to '1.2.0'
    version_tag = normalize_version(version_tag)
    validate_semantic_version(version_tag)

    # 2. Get and validate course content with relationships
    course_content = db.query(CourseContent).options(
        joinedload(CourseContent.course),
        joinedload(CourseContent.course_content_type).joinedload(CourseContentType.course_content_kind)
    ).filter(CourseContent.id == course_content_id).first()

    if not course_content:
        raise NotFoundException(
            error_code="CONTENT_001",
            detail="Course content not found",
            context={"course_content_id": str(course_content_id)}
        )

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
            error_code="AUTHZ_001",
            detail="You don't have permission to assign examples to this course",
            context={
                "course_content_id": str(course_content_id),
                "course_id": str(course_content.course_id)
            }
        )

    # 4. Validate course content is submittable (assignment)
    content_type = course_content.course_content_type
    if not content_type or not content_type.course_content_kind:
        raise BadRequestException(
            error_code="CONTENT_002",
            detail="Course content has no content type or kind",
            context={"course_content_id": str(course_content_id)}
        )

    if not content_type.course_content_kind.submittable:
        raise BadRequestException(
            error_code="CONTENT_003",
            detail="Cannot assign examples to non-submittable content",
            context={
                "course_content_id": str(course_content_id),
                "content_kind": content_type.course_content_kind.id,
                "is_submittable": False
            }
        )

    # 5. Resolve example by ID or identifier
    if example_identifier:
        # Look up by identifier (ltree path)
        example = db.query(Example).filter(Example.identifier == Ltree(example_identifier)).first()
        if not example:
            raise NotFoundException(
                error_code="CONTENT_004",
                detail="Example not found by identifier",
                context={"example_identifier": example_identifier}
            )
        example_id = example.id
    else:
        # Look up by ID
        example = db.query(Example).filter(Example.id == example_id).first()
        if not example:
            raise NotFoundException(
                error_code="CONTENT_004",
                detail="Example not found",
                context={"example_id": str(example_id)}
            )

    # 6. Find specific version
    example_version = db.query(ExampleVersion).filter(
        and_(
            ExampleVersion.example_id == example_id,
            ExampleVersion.version_tag == version_tag
        )
    ).first()

    if not example_version:
        raise NotFoundException(
            error_code="CONTENT_005",
            detail=f"Example version '{version_tag}' not found",
            context={
                "example_id": str(example_id),
                "version_tag": version_tag
            }
        )

    # 7. Check if deployment already exists
    existing_deployment = db.query(CourseContentDeployment).filter(
        CourseContentDeployment.course_content_id == course_content_id
    ).first()

    if existing_deployment:
        # Validate reassignment using shared helper function
        is_same_example, action = validate_reassignment_allowed(
            existing_deployment=existing_deployment,
            new_example_identifier=str(example.identifier),
            course_content_id=str(course_content_id)
        )

        # Track previous version for history
        previous_version_id = existing_deployment.example_version_id

        # Set appropriate log message
        if is_same_example:
            log_message = f"Updated example {example_id} from v{existing_deployment.version_tag} to v{version_tag}"
        else:
            log_message = f"Reassigned from {existing_deployment.example_identifier} to {example.identifier} (v{version_tag})"

        # Update deployment
        existing_deployment.example_version_id = example_version.id
        existing_deployment.example_identifier = example.identifier
        existing_deployment.version_tag = version_tag
        existing_deployment.deployment_path = str(example.identifier)  # Set deployment path to example identifier
        existing_deployment.deployment_status = 'pending'  # Reset to pending for redeployment
        existing_deployment.assigned_at = datetime.now(timezone.utc)
        existing_deployment.deployment_message = None
        existing_deployment.updated_by = permissions.user_id

        # Create history entry
        history = DeploymentHistory(
            deployment_id=existing_deployment.id,
            action=action,
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
            f"{log_message} for content {course_content_id} "
            f"(status reset to pending for redeployment)"
        )

        return existing_deployment

    else:
        # Create new deployment
        deployment = CourseContentDeployment(
            course_content_id=course_content_id,
            example_version_id=example_version.id,
            example_identifier=example.identifier,
            version_tag=version_tag,
            deployment_path=str(example.identifier),  # Set deployment path to example identifier by default
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
        raise NotFoundException(
            error_code="CONTENT_001",
            detail="Course content not found",
            context={"course_content_id": str(course_content_id)}
        )

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
            error_code="AUTHZ_001",
            detail="You don't have permission to view deployments for this course",
            context={
                "course_content_id": str(course_content_id),
                "course_id": str(course_content.course_id)
            }
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
        raise NotFoundException(
            error_code="CONTENT_001",
            detail="Course content not found",
            context={"course_content_id": str(course_content_id)}
        )

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
            error_code="AUTHZ_001",
            detail="You don't have permission to unassign examples from this course",
            context={
                "course_content_id": str(course_content_id),
                "course_id": str(course_content.course_id)
            }
        )

    # Get deployment
    deployment = db.query(CourseContentDeployment).filter(
        CourseContentDeployment.course_content_id == course_content_id
    ).first()

    if not deployment:
        raise NotFoundException(
            error_code="DEPLOY_002",
            detail="No example assigned to this course content",
            context={"course_content_id": str(course_content_id)}
        )

    # Check if already deployed
    if deployment.deployment_status in ('deployed', 'deploying'):
        raise BadRequestException(
            error_code="DEPLOY_001",
            detail="Cannot unassign: Example is already deployed or being deployed",
            context={
                "course_content_id": str(course_content_id),
                "current_status": deployment.deployment_status
            }
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
            error_code="AUTHZ_003",
            detail="You don't have permission to validate content for this course",
            context={"course_id": str(course_id)}
        )

    # 2. Extract all unique example identifiers and build content map
    identifiers = []  # Changed from set() to list to preserve order and handle any type
    content_map = {}  # content_id -> validation_item

    for item in content_validations:
        # Extract identifier (should already be a string from Pydantic validation)
        identifier = str(item['example_identifier'])

        # # Convert list/tuple to dot-separated string (frontend sends arrays)
        # if isinstance(identifier, (list, tuple)):
        #     identifier = '.'.join(str(part) for part in identifier)
        #     item['example_identifier'] = identifier
        # elif not isinstance(identifier, str):
        #     identifier = str(identifier)
        #     item['example_identifier'] = identifier

        # Add to identifiers list if not already present
        if identifier not in identifiers:
            identifiers.append(identifier)
        content_map[item['content_id']] = item

    # 3. Batch fetch all examples by identifier
    # Use OR conditions for ltree equality comparisons (ltree doesn't support IN operator)
    if not identifiers:
        examples = []
    else:
        # Build OR conditions: wrap string identifiers in Ltree() for proper SQLAlchemy binding
        # Use backend's Ltree class which SQLAlchemy-utils expects (has .path property)
        ltree_conditions = [Example.identifier == Ltree(identifier) for identifier in identifiers]
        examples = db.query(Example).filter(or_(*ltree_conditions)).all()

    # Build example lookup map: identifier -> example
    example_map = {str(ex.identifier): ex for ex in examples}

    # 4. Get all example IDs for version lookup
    example_ids = [ex.id for ex in examples]

    # 5. Batch fetch all versions for these examples
    if not example_ids:
        versions = []
    else:
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
