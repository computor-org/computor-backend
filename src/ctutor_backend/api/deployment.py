"""
API endpoints for deployment operations.
"""

import logging
from typing import Annotated, Optional, Dict, Any
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ctutor_backend.permissions.principal import Principal
from .auth import get_current_principal

# Import business logic
from ctutor_backend.business_logic.deployment import (
    deploy_from_configuration,
    deploy_from_yaml_file,
    get_deployment_workflow_status,
    validate_deployment_configuration,
)
from .exceptions import BadRequestException

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
    try:
        result = deploy_from_configuration(
            request.deployment_config,
            permissions,
            request.validate_only
        )

        return DeploymentResponse(**result)

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
    try:
        # Read file content
        content = await file.read()

        result = await deploy_from_yaml_file(
            content,
            file.filename,
            permissions,
            validate_only
        )

        return DeploymentResponse(**result)

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
    try:
        return await get_deployment_workflow_status(workflow_id, permissions)

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
    return validate_deployment_configuration(request.deployment_config, permissions)
