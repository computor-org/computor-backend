"""
Deployment mapping utilities for converting CSV/table data to deployment configurations.

This module provides tools to map arbitrary table/CSV fields into UserDeployment,
AccountDeployment, and CourseMemberDeployment configurations using a JSON-configurable
mapping schema.
"""

from .config import (
    FieldMappingConfig,
    UserFieldsConfig,
    AccountFieldsConfig,
    CourseMemberFieldsConfig,
    TransformationsConfig,
    DeploymentMappingConfig,
)
from .mapper import DeploymentMapper, MappingError
from .transformers import FieldTransformer

__all__ = [
    "FieldMappingConfig",
    "UserFieldsConfig",
    "AccountFieldsConfig",
    "CourseMemberFieldsConfig",
    "TransformationsConfig",
    "DeploymentMappingConfig",
    "DeploymentMapper",
    "MappingError",
    "FieldTransformer",
]
