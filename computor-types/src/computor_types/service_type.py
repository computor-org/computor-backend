"""
Service Type DTOs - Pure Pydantic models for service type data.

Service types define the kinds of services available in the system using
a UUID + Ltree hybrid approach for stable references and hierarchical organization.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import datetime

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery


class ServiceTypeBase(BaseModel):
    """Base fields shared across all service type DTOs."""
    path: str = Field(..., description="Hierarchical path (e.g., 'testing.python', 'review.llm.gpt4')")
    name: str = Field(..., min_length=1, max_length=255, description="Display name")
    description: Optional[str] = Field(None, description="Detailed description")
    category: str = Field(..., max_length=63, description="Category: worker, testing, review, metrics, integration")
    plugin_module: Optional[str] = Field(None, max_length=255, description="Python module providing functionality")
    schema_: Optional[dict] = Field(None, alias="schema", description="JSON Schema for config validation")
    icon: Optional[str] = Field(None, max_length=255, description="Icon identifier")
    color: Optional[str] = Field(None, max_length=7, description="Hex color for UI (e.g., #FF5733)")
    enabled: bool = Field(True, description="Whether this service type is enabled")
    properties: Optional[dict] = Field(default_factory=dict, description="Additional properties")

    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate ltree path format."""
        import re
        if not re.match(r'^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)*$', v):
            raise ValueError(
                f"Invalid ltree path: '{v}'. "
                f"Path must contain only letters, numbers, underscores, and hyphens, "
                f"with segments separated by dots."
            )
        return v

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format."""
        if v is None:
            return v
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError(f"Invalid hex color: '{v}'. Must be in format #RRGGBB")
        return v

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is one of the allowed values."""
        allowed = ['worker', 'testing', 'review', 'metrics', 'integration', 'custom']
        if v not in allowed:
            raise ValueError(
                f"Invalid category: '{v}'. "
                f"Must be one of: {', '.join(allowed)}"
            )
        return v


class ServiceTypeCreate(ServiceTypeBase):
    """DTO for creating a new service type."""
    pass


class ServiceTypeUpdate(BaseModel):
    """DTO for updating an existing service type."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, max_length=63)
    plugin_module: Optional[str] = Field(None, max_length=255)
    schema_: Optional[dict] = Field(None, alias="schema")
    icon: Optional[str] = Field(None, max_length=255)
    color: Optional[str] = Field(None, max_length=7)
    enabled: Optional[bool] = None
    properties: Optional[dict] = None

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format."""
        if v is None:
            return v
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError(f"Invalid hex color: '{v}'. Must be in format #RRGGBB")
        return v

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Validate category is one of the allowed values."""
        if v is None:
            return v
        allowed = ['worker', 'testing', 'review', 'metrics', 'integration', 'custom']
        if v not in allowed:
            raise ValueError(
                f"Invalid category: '{v}'. "
                f"Must be one of: {', '.join(allowed)}"
            )
        return v


class ServiceTypeList(BaseEntityList):
    """DTO for listing service types (minimal fields)."""
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )

    id: str = Field(..., description="UUID")
    path: str = Field(..., description="Hierarchical path")
    name: str = Field(..., description="Display name")
    category: str = Field(..., description="Category")
    enabled: bool = Field(..., description="Enabled status")
    icon: Optional[str] = Field(None, description="Icon identifier")
    color: Optional[str] = Field(None, description="Hex color")

    @field_validator('path', mode='before')
    @classmethod
    def convert_ltree_to_str(cls, v: Any) -> str:
        """Convert Ltree objects to strings."""
        if v is None:
            return ""
        # If it's already a string, return it
        if isinstance(v, str):
            return v
        # Otherwise convert to string (handles Ltree objects)
        return str(v)


class ServiceTypeGet(BaseEntityGet):
    """DTO for getting a single service type (full fields)."""
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )

    id: str = Field(..., description="UUID")
    path: str = Field(..., description="Hierarchical path")
    name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Description")
    category: str = Field(..., description="Category")
    plugin_module: Optional[str] = Field(None, description="Python module")
    schema_: Optional[dict] = Field(None, alias="schema", description="JSON Schema")
    icon: Optional[str] = Field(None, description="Icon identifier")
    color: Optional[str] = Field(None, description="Hex color")
    enabled: bool = Field(..., description="Enabled status")
    properties: dict = Field(default_factory=dict, description="Additional properties")
    version: int = Field(..., description="Version number")

    @field_validator('path', mode='before')
    @classmethod
    def convert_ltree_to_str(cls, v: Any) -> str:
        """Convert Ltree objects to strings."""
        if v is None:
            return ""
        if isinstance(v, str):
            return v
        return str(v)


class ServiceTypeQuery(ListQuery):
    """Query parameters for filtering service types."""
    id: Optional[str] = Field(None, description="Filter by UUID")
    path: Optional[str] = Field(None, description="Filter by exact path")
    path_descendant: Optional[str] = Field(None, description="Filter by path descendants (e.g., 'testing' returns all testing.*)")
    path_pattern: Optional[str] = Field(None, description="Filter by path pattern (ltree lquery)")
    category: Optional[str] = Field(None, description="Filter by category")
    enabled: Optional[bool] = Field(None, description="Filter by enabled status")
    plugin_module: Optional[str] = Field(None, description="Filter by plugin module")


class ServiceTypeInterface(EntityInterface):
    """
    Service Type entity interface - pure DTO definitions.

    Defines the data structure for service type CRUD operations.
    Backend concerns (model, endpoint, caching) are in BackendEntityInterface.
    """
    create = ServiceTypeCreate
    get = ServiceTypeGet
    list = ServiceTypeList
    update = ServiceTypeUpdate
    query = ServiceTypeQuery
