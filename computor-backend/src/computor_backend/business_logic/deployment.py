"""Business logic for deployment operations."""
import logging
import yaml
from typing import Dict, Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from computor_types.deployments_refactored import ComputorDeploymentConfig
from computor_backend.permissions.principal import Principal
from computor_backend.tasks import get_task_executor, TaskSubmission
from computor_backend.api.exceptions import BadRequestException, ForbiddenException
from computor_backend.api.permissions import check_admin

logger = logging.getLogger(__name__)


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

    # Submit to Temporal workflow
    task_executor = get_task_executor()
    workflow_id = f"deploy-{uuid4()}"

    task_submission = TaskSubmission(
        task_name="deploy_computor_hierarchy",
        parameters={
            "deployment_config": config.model_dump(),
            "user_id": str(permissions.user_id)
        },
        queue="computor-tasks",
        workflow_id=workflow_id
    )

    # Note: This is synchronous in the refactored version
    # The original was async, but task_executor.submit_task may not be async
    # Keeping the structure the same for now
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
        raise BadRequestException(f"Invalid YAML format: {str(e)}")

    # Convert to deployment configuration
    config = ComputorDeploymentConfig(**yaml_data)

    if validate_only:
        return {
            "workflow_id": "validation-only",
            "status": "validated",
            "message": "YAML configuration is valid",
            "deployment_path": config.get_full_course_path()
        }

    # Submit to Temporal workflow
    task_executor = get_task_executor()
    workflow_id = f"deploy-yaml-{uuid4()}"

    task_submission = TaskSubmission(
        task_name="deploy_computor_hierarchy",
        parameters={
            "deployment_config": config.model_dump(),
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
