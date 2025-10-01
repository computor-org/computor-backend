from enum import Enum
from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field, EmailStr
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.orm import Session
from ctutor_backend.interface.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery
from ctutor_backend.model.organization import Organization
from ..custom_types import Ltree
import re

if TYPE_CHECKING:
    from ctutor_backend.interface.deployments import GitLabConfig, GitLabConfigGet

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

def organization_search(db: Session, query, params: Optional[OrganizationQuery]):
    if params.id != None:
        query = query.filter(Organization.id == params.id)
    if params.title != None:
        query = query.filter(Organization.title == params.title)
    if params.description != None:
        query = query.filter(Organization.description == params.description)
    if params.path != None:
        query = query.filter(Organization.path == Ltree(params.path))
    if params.organization_type != None:
        query = query.filter(Organization.organization_type == params.organization_type)
    if params.user_id != None:
        query = query.filter(Organization.user_id == params.user_id)
    if params.number != None:
        query = query.filter(Organization.number == params.number)
    if params.email != None:
        query = query.filter(Organization.email == params.email)
    if params.telephone != None:
        query = query.filter(Organization.telephone == params.telephone)
    if params.fax_number != None:
        query = query.filter(Organization.fax_number == params.fax_number)
    if params.url != None:
        query = query.filter(Organization.url == params.url)
    if params.postal_code != None:
        query = query.filter(Organization.postal_code == params.postal_code)
    if params.street_address != None:
        query = query.filter(Organization.street_address == params.street_address)
    if params.locality != None:
        query = query.filter(Organization.locality == params.locality)
    if params.region != None:
        query = query.filter(Organization.region == params.region)
    if params.country != None:
        query = query.filter(Organization.country == params.country)

    return query

class OrganizationInterface(EntityInterface):
    create = OrganizationCreate
    get = OrganizationGet
    list = OrganizationList
    update = OrganizationUpdate
    query = OrganizationQuery
    search = organization_search
    endpoint = "organizations"
    model = Organization
    cache_ttl = 600  # 10 minutes cache for organization data (changes less frequently)

# Import GitLabConfig after OrganizationProperties is defined to avoid circular import
from ctutor_backend.interface.deployments import GitLabConfig, GitLabConfigGet
# Rebuild the models to resolve forward references
OrganizationProperties.model_rebuild()
OrganizationPropertiesGet.model_rebuild()