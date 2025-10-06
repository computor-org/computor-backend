from enum import Enum
from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field, EmailStr
from typing import TYPE_CHECKING, Optional
from datetime import datetime

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

from computor_types.custom_types import Ltree
import re

if TYPE_CHECKING:
        from computor_types.deployments import GitLabConfig, GitLabConfigGet

class OrganizationType(str,Enum):
    user = "user"
    community = "community"
    organization = "organization"

class OrganizationProperties(BaseModel):
    gitlab: Optional['GitLabConfig'] = None

    model_config = ConfigDict(
        extra='allow',
    )

class OrganizationPropertiesGet(BaseModel):
    gitlab: Optional['GitLabConfigGet'] = None

    model_config = ConfigDict(
        extra='allow',
    )

class OrganizationCreate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Organization title")
    description: Optional[str] = Field(None, max_length=4096, description="Organization description")
    path: str = Field(min_length=1, description="Hierarchical path (ltree format)")
    organization_type: OrganizationType = Field(description="Type of organization")
    user_id: Optional[str] = Field(None, description="Associated user ID (for user type organizations)")
    properties: Optional[OrganizationProperties] = Field(None, description="Additional properties")
    number: Optional[str] = Field(None, max_length=255, description="Organization number/identifier")
    email: Optional[EmailStr] = Field(None, description="Contact email address")
    telephone: Optional[str] = Field(None, max_length=255, description="Phone number")
    fax_number: Optional[str] = Field(None, max_length=255, description="Fax number")
    url: Optional[str] = Field(None, max_length=2048, description="Organization website URL")
    postal_code: Optional[str] = Field(None, max_length=255, description="Postal/ZIP code")
    street_address: Optional[str] = Field(None, max_length=1024, description="Street address")
    locality: Optional[str] = Field(None, max_length=255, description="City/locality")
    region: Optional[str] = Field(None, max_length=255, description="State/region")
    country: Optional[str] = Field(None, max_length=255, description="Country")
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v):
        if not v:
            raise ValueError('Path cannot be empty')
        # Basic ltree path validation
        if not re.match(r'^[a-zA-Z0-9_-]+(\.?[a-zA-Z0-9_-]+)*$', v):
            raise ValueError('Path must be valid ltree format (alphanumeric, underscores, hyphens, dots)')
        return v
    
    @model_validator(mode='after')
    @classmethod
    def validate_organization_constraints(cls, values):
        org_type = values.organization_type
        title = values.title
        user_id = values.user_id
        
        # Title validation
        if org_type == OrganizationType.user and title is not None:
            raise ValueError('User organizations cannot have a title')
        elif org_type != OrganizationType.user and not title:
            raise ValueError('Non-user organizations must have a title')
            
        # User ID validation
        if org_type == OrganizationType.user and not user_id:
            raise ValueError('User organizations must have a user_id')
        elif org_type != OrganizationType.user and user_id is not None:
            raise ValueError('Non-user organizations cannot have a user_id')
            
        return values
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    model_config = ConfigDict(use_enum_values=True)

class OrganizationGet(BaseEntityGet):
    id: str = Field(description="Organization unique identifier")
    path: str = Field(description="Hierarchical path")
    title: Optional[str] = Field(None, description="Organization title")
    description: Optional[str] = Field(None, description="Organization description")
    organization_type: OrganizationType = Field(description="Type of organization")
    user_id: Optional[str] = Field(None, description="Associated user ID")
    properties: Optional[OrganizationPropertiesGet] = Field(None, description="Additional properties")
    number: Optional[str] = Field(None, description="Organization number")
    email: Optional[EmailStr] = Field(None, description="Contact email")
    telephone: Optional[str] = Field(None, description="Phone number")
    fax_number: Optional[str] = Field(None, description="Fax number")
    url: Optional[str] = Field(None, description="Website URL")
    postal_code: Optional[str] = Field(None, description="Postal code")
    street_address: Optional[str] = Field(None, description="Street address")
    locality: Optional[str] = Field(None, description="City/locality")
    region: Optional[str] = Field(None, description="State/region")
    country: Optional[str] = Field(None, description="Country")
    
    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)
    
    @property
    def display_name(self) -> str:
        """Get display name for the organization"""
        if self.title:
            return self.title
        if self.organization_type == OrganizationType.user:
            return f"User Organization ({self.path})"
        return f"Organization ({self.path})"
    
    @property
    def path_components(self) -> list[str]:
        """Get path components as a list"""
        return self.path.split('.') if self.path else []
    
    @property
    def parent_path(self) -> Optional[str]:
        """Get the parent path"""
        components = self.path_components
        return '.'.join(components[:-1]) if len(components) > 1 else None
    
    model_config = ConfigDict(use_enum_values=True, from_attributes=True)

class OrganizationList(BaseEntityList):
    id: str = Field(description="Organization unique identifier")
    path: str = Field(description="Hierarchical path")
    title: Optional[str] = Field(None, description="Organization title")
    organization_type: OrganizationType = Field(description="Type of organization")
    user_id: Optional[str] = Field(None, description="Associated user ID")
    email: Optional[EmailStr] = Field(None, description="Contact email")
    
    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)
    
    @property
    def display_name(self) -> str:
        """Get display name for lists"""
        if self.title:
            return self.title
        return f"{self.organization_type.title()} ({self.path})"
    
    model_config = ConfigDict(use_enum_values=True, from_attributes=True)

class OrganizationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    organization_type: Optional[OrganizationType] = None
    user_id: Optional[str] = None
    properties: Optional[OrganizationProperties] = None
    number: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    fax_number: Optional[str] = None
    url: Optional[str] = None
    postal_code: Optional[str] = None
    street_address: Optional[str] = None
    locality: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)

class OrganizationQuery(ListQuery):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    organization_type: Optional[OrganizationType] = None
    user_id: Optional[str] = None
    properties: Optional[OrganizationProperties] = None
    number: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    fax_number: Optional[str] = None
    url: Optional[str] = None
    postal_code: Optional[str] = None
    street_address: Optional[str] = None
    locality: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class OrganizationInterface(EntityInterface):
    create = OrganizationCreate
    get = OrganizationGet
    list = OrganizationList
    update = OrganizationUpdate
    query = OrganizationQuery

# Import GitLabConfig after OrganizationProperties is defined to avoid circular import
from computor_types.deployments import GitLabConfig, GitLabConfigGet
# Rebuild the models to resolve forward references
OrganizationProperties.model_rebuild()
OrganizationPropertiesGet.model_rebuild()