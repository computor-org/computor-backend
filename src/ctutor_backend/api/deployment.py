"""
API endpoints for deployment operations.
"""

import logging
import yaml
from typing import Annotated, Optional, Dict, Any
from uuid import uuid4
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..interface.deployments_refactored import (
    ComputorDeploymentConfig,
    DeploymentFactory
)
from ctutor_backend.permissions.principal import Principal
from ..tasks import get_task_executor, TaskSubmission
from .auth import get_current_principal
from .permissions import check_admin
from .exceptions import BadRequestException, ForbiddenException

logger = logging.getLogger(__name__)
deployment_router = APIRouter()


class DeploymentRequest(BaseModel):
    """Request model for deployment from configuration."""
    deployment_config: Dict[str, Any] = Field(
        description="Deployment configuration as dictionary"
    )
    validate_only: bool = Field(
        False,
        description="If true, only validate the configuration without deploying"
    )


class DeploymentResponse(BaseModel):
    """Response model for deployment operations."""
    workflow_id: str = Field(description="Temporal workflow ID")
    status: str = Field(description="Deployment status")
    message: str = Field(description="Status message")
    deployment_path: Optional[str] = Field(None, description="Full deployment path")


@deployment_router.post("/deploy/from-config", response_model=DeploymentResponse)
async def deploy_from_config(
    request: DeploymentRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
) -> DeploymentResponse:
    """
    Deploy organization -> course family -> course hierarchy from configuration.
    
    Requires admin permissions.
    """
    # Check admin permissions
    if not check_admin(permissions):
        raise ForbiddenException("Admin permissions required for deployment")
    
    try:
        # Validate configuration
        config = ComputorDeploymentConfig(**request.deployment_config)
        
        if request.validate_only:
            return DeploymentResponse(
                workflow_id="validation-only",
                status="validated",
                message="Configuration is valid",
                deployment_path=config.get_full_course_path()
            )
        
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
        
        result = await task_executor.submit_task(task_submission)
        
        return DeploymentResponse(
            workflow_id=workflow_id,
            status="submitted",
            message="Deployment workflow started",
            deployment_path=config.get_full_course_path()
        )
        
    except ValueError as e:
        raise BadRequestException(f"Invalid configuration: {str(e)}")
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}"
        )


@deployment_router.post("/deploy/from-yaml", response_model=DeploymentResponse)
async def deploy_from_yaml(
    file: UploadFile = File(..., description="YAML deployment configuration file"),
    validate_only: bool = False,
    permissions: Annotated[Principal, Depends(get_current_principal)] = None,
    db: Session = Depends(get_db)
) -> DeploymentResponse:
    """
    Deploy organization -> course family -> course hierarchy from YAML file.
    
    Requires admin permissions.
    """
    # Check admin permissions
    if not check_admin(permissions):
        raise ForbiddenException("Admin permissions required for deployment")
    
    # Check file type
    if not file.filename.endswith(('.yaml', '.yml')):
        raise BadRequestException("File must be a YAML file (.yaml or .yml)")
    
    try:
        # Read and parse YAML file
        content = await file.read()
        yaml_data = yaml.safe_load(content)
        
        # Convert to deployment configuration
        config = ComputorDeploymentConfig(**yaml_data)
        
        if validate_only:
            return DeploymentResponse(
                workflow_id="validation-only",
                status="validated",
                message="YAML configuration is valid",
                deployment_path=config.get_full_course_path()
            )
        
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
        
        return DeploymentResponse(
            workflow_id=workflow_id,
            status="submitted",
            message=f"Deployment workflow started from {file.filename}",
            deployment_path=config.get_full_course_path()
        )
        
    except yaml.YAMLError as e:
        raise BadRequestException(f"Invalid YAML format: {str(e)}")
    except ValueError as e:
        raise BadRequestException(f"Invalid configuration: {str(e)}")
    except Exception as e:
        logger.error(f"Deployment from YAML failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}"
        )


@deployment_router.get("/deploy/status/{workflow_id}")
async def get_deployment_status(
    workflow_id: str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get the status of a deployment workflow.
    
    Requires admin permissions.
    """
    # Check admin permissions
    if not check_admin(permissions):
        raise ForbiddenException("Admin permissions required")
    
    try:
        task_executor = get_task_executor()
        status = await task_executor.get_task_status(workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "status": status.get("status", "unknown"),
            "result": status.get("result"),
            "error": status.get("error")
        }
        
    except Exception as e:
        logger.error(f"Failed to get deployment status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@deployment_router.post("/deploy/validate")
async def validate_deployment_config(
    request: DeploymentRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Validate a deployment configuration without deploying.
    
    Requires admin permissions.
    """
    # Check admin permissions
    if not check_admin(permissions):
        raise ForbiddenException("Admin permissions required")
    
    try:
        # Validate configuration
        config = ComputorDeploymentConfig(**request.deployment_config)
        
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
