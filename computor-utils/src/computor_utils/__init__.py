"""Computor Utils - Shared utility functions for Computor platform."""

__version__ = "0.1.0"

from .vsix_utils import parse_vsix_metadata
from .deployment_mapping import (
    DeploymentMapper,
    DeploymentMappingConfig,
    FieldTransformer,
)

__all__ = [
    "parse_vsix_metadata",
    "DeploymentMapper",
    "DeploymentMappingConfig",
    "FieldTransformer",
]
