"""Business logic for deployment operations."""
import logging
import yaml
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from computor_types.deployments_refactored import ComputorDeploymentConfig
from computor_backend.database import get_db_session
from computor_backend.permissions.principal import Principal
from computor_backend.tasks import get_task_executor, TaskSubmission
from computor_backend.exceptions import BadRequestException, ForbiddenException
from computor_backend.permissions.core import check_admin

logger = logging.getLogger(__name__)


def create_organization_sync(org_config: Dict[str, Any], user_id: str, db: Session) -> str:
    """Create an organization row and enroll the creator as ``_owner``.

    Course-level git model: organizations carry no git configuration, so this
    is a plain DB insert — no Temporal activity needed. Idempotent on
    (organization_type, path). Returns the organization id.
    """
    from computor_backend.custom_types import Ltree
    from computor_backend.model.organization import Organization, OrganizationMember

    org_type = org_config.get("organization_type") or "organization"
    org = (
        db.query(Organization)
        .filter(
            Organization.organization_type == org_type,
            Organization.path == Ltree(org_config["path"]),
        )
        .first()
    )
    if org is None:
        org = Organization(
            title=org_config.get("name"),
            description=org_config.get("description", ""),
            path=Ltree(org_config["path"]),
            organization_type=org_type,
            properties={},
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(org)
        db.flush()

    # Idempotent on unique (user_id, organization_id).
    if user_id and (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user_id,
        )
        .first()
    ) is None:
        db.add(OrganizationMember(
            organization_id=org.id,
            user_id=user_id,
            organization_role_id="_owner",
            created_by=user_id,
            updated_by=user_id,
        ))

    db.commit()
    logger.info("Created organization (course-level git model): %s (ID: %s)", org_config.get("path"), org.id)
    return str(org.id)


def create_course_family_sync(
    family_config: Dict[str, Any], organization_id: str, user_id: str, db: Session
) -> str:
    """Create a course family row and enroll the creator as ``_owner``.

    Course families carry no git config (git is per-course), so this is a plain
    DB insert. Idempotent on (organization_id, path). Returns the family id.
    """
    from computor_backend.custom_types import Ltree
    from computor_backend.model.organization import Organization
    from computor_backend.model.course import CourseFamily, CourseFamilyMember

    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if not org:
        raise ValueError(f"Organization {organization_id} not found")

    family = (
        db.query(CourseFamily)
        .filter(
            CourseFamily.organization_id == org.id,
            CourseFamily.path == Ltree(family_config["path"]),
        )
        .first()
    )
    if family is None:
        family = CourseFamily(
            title=family_config.get("name"),
            description=family_config.get("description", "") or "",
            path=Ltree(family_config["path"]),
            organization_id=org.id,
            properties={},
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(family)
        db.flush()

    # Idempotent on unique (user_id, course_family_id).
    if user_id and (
        db.query(CourseFamilyMember)
        .filter(
            CourseFamilyMember.course_family_id == family.id,
            CourseFamilyMember.user_id == user_id,
        )
        .first()
    ) is None:
        db.add(CourseFamilyMember(
            course_family_id=family.id,
            user_id=user_id,
            course_family_role_id="_owner",
            created_by=user_id,
            updated_by=user_id,
        ))

    db.commit()
    logger.info("Created course family: %s (ID: %s)", family_config.get("path"), family.id)
    return str(family.id)


def precreate_hierarchy_and_collect_courses(
    config: ComputorDeploymentConfig, user_id: str, db: Session
) -> List[Dict[str, Any]]:
    """Create every organization + course family synchronously (course-level
    git model — plain DB inserts) and return the flat list of courses still to
    be created via the deploy workflow: ``[{course_config, course_family_id}]``.
    """
    courses: List[Dict[str, Any]] = []
    for org in config.organizations:
        org_id = create_organization_sync(org.model_dump(), user_id, db)
        for family in org.course_families:
            family_id = create_course_family_sync(family.model_dump(), org_id, user_id, db)
            for course in family.courses:
                courses.append({
                    "course_config": course.model_dump(),
                    "course_family_id": family_id,
                })
    return courses


def deploy_from_configuration(
    deployment_config: Dict[str, Any],
    permissions: Principal,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Deploy organization -> course family -> course hierarchy from configuration.

    Args:
        deployment_config: Deployment configuration as dictionary
        permissions: Current user permissions
        validate_only: If true, only validate without deploying

    Returns:
        Dictionary with workflow_id, status, message, deployment_path

    Raises:
        ForbiddenException: If user is not admin
        BadRequestException: If configuration is invalid
        Exception: If deployment fails
    """
    # Check admin permissions
    if not check_admin(permissions):
        raise ForbiddenException("Admin permissions required for deployment")

    # Validate configuration
    config = ComputorDeploymentConfig(**deployment_config)

    if validate_only:
        return {
            "workflow_id": "validation-only",
            "status": "validated",
            "message": "Configuration is valid",
            "deployment_path": config.get_full_course_path()
        }

    # Organizations + course families are plain DB inserts (course-level git
    # model) — create them synchronously here, then let the workflow create only
    # the courses (which still need Temporal for git / student-template setup).
    with get_db_session() as db:
        courses = precreate_hierarchy_and_collect_courses(config, str(permissions.user_id), db)

    # Submit to Temporal workflow
    task_executor = get_task_executor()
    workflow_id = f"deploy-{uuid4()}"

    task_submission = TaskSubmission(
        task_name="deploy_computor_hierarchy",
        parameters={
            "courses": courses,
            "user_id": str(permissions.user_id)
        },
        queue="computor-tasks",
        workflow_id=workflow_id
    )

    result = task_executor.submit_task(task_submission)

    return {
        "workflow_id": workflow_id,
        "status": "submitted",
        "message": "Deployment workflow started",
        "deployment_path": config.get_full_course_path()
    }


async def deploy_from_yaml_file(
    file_content: bytes,
    filename: str,
    permissions: Principal,
    validate_only: bool = False,
) -> Dict[str, Any]:
    """Deploy organization -> course family -> course hierarchy from YAML file.

    Args:
        file_content: YAML file content as bytes
        filename: Original filename
        permissions: Current user permissions
        validate_only: If true, only validate without deploying

    Returns:
        Dictionary with workflow_id, status, message, deployment_path

    Raises:
        ForbiddenException: If user is not admin
        BadRequestException: If file format or configuration is invalid
        Exception: If deployment fails
    """
    # Check admin permissions
    if not check_admin(permissions):
        raise ForbiddenException("Admin permissions required for deployment")

    # Check file type
    if not filename.endswith(('.yaml', '.yml')):
        raise BadRequestException("File must be a YAML file (.yaml or .yml)")

    # Parse YAML file
    try:
        yaml_data = yaml.safe_load(file_content)
    except yaml.YAMLError as e:
        raise BadRequestException(f"Invalid YAML format: {str(e)}") from e

    # Convert to deployment configuration
    config = ComputorDeploymentConfig(**yaml_data)

    if validate_only:
        return {
            "workflow_id": "validation-only",
            "status": "validated",
            "message": "YAML configuration is valid",
            "deployment_path": config.get_full_course_path()
        }

    # Create organizations + course families synchronously (plain DB inserts),
    # then submit only the courses to the workflow.
    with get_db_session() as db:
        courses = precreate_hierarchy_and_collect_courses(config, str(permissions.user_id), db)

    # Submit to Temporal workflow
    task_executor = get_task_executor()
    workflow_id = f"deploy-yaml-{uuid4()}"

    task_submission = TaskSubmission(
        task_name="deploy_computor_hierarchy",
        parameters={
            "courses": courses,
            "user_id": str(permissions.user_id)
        },
        queue="computor-tasks",
        workflow_id=workflow_id
    )

    result = await task_executor.submit_task(task_submission)

    return {
        "workflow_id": workflow_id,
        "status": "submitted",
        "message": f"Deployment workflow started from {filename}",
        "deployment_path": config.get_full_course_path()
    }


async def get_deployment_workflow_status(
    workflow_id: str,
    permissions: Principal,
) -> Dict[str, Any]:
    """Get the status of a deployment workflow.

    Args:
        workflow_id: Temporal workflow ID
        permissions: Current user permissions

    Returns:
        Dictionary with workflow_id, status, result, error

    Raises:
        ForbiddenException: If user is not admin
        Exception: If status check fails
    """
    # Check admin permissions
    if not check_admin(permissions):
        raise ForbiddenException("Admin permissions required")

    task_executor = get_task_executor()
    status = await task_executor.get_task_status(workflow_id)

    return {
        "workflow_id": workflow_id,
        "status": status.get("status", "unknown"),
        "result": status.get("result"),
        "error": status.get("error")
    }


def validate_deployment_configuration(
    deployment_config: Dict[str, Any],
    permissions: Principal,
) -> Dict[str, Any]:
    """Validate a deployment configuration without deploying.

    Args:
        deployment_config: Deployment configuration as dictionary
        permissions: Current user permissions

    Returns:
        Dictionary with validation results including:
        - valid: bool
        - errors: list of error messages
        - warnings: list of warning messages
        - info: deployment information

    Raises:
        ForbiddenException: If user is not admin
    """
    # Check admin permissions
    if not check_admin(permissions):
        raise ForbiddenException("Admin permissions required")

    try:
        # Validate configuration
        config = ComputorDeploymentConfig(**deployment_config)

        # Perform additional validation
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": {
                "organizations_count": len(config.organizations),
                "total_courses": sum(
                    len(family.courses)
                    for org in config.organizations
                    for family in org.course_families
                ),
                "entity_counts": config.count_entities(),
                "deployment_paths": config.get_deployment_paths(),
                "full_path": config.get_full_course_path()
            }
        }

        # Check for potential issues
        if not config.organizations:
            validation_result["errors"].append("At least one organization must be configured")
            validation_result["valid"] = False

        for org in config.organizations:
            if not org.gitlab and not org.github:
                validation_result["warnings"].append(
                    f"No repository configuration (GitLab/GitHub) specified for organization '{org.name}'"
                )

            for family in org.course_families:
                for course in family.courses:
                    if not course.execution_backends:
                        validation_result["warnings"].append(
                            f"No execution backends configured for course '{course.name}' in '{org.name}/{family.name}'"
                        )

        return validation_result

    except ValueError as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "warnings": [],
            "info": {}
        }
