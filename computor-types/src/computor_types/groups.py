from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional


    
from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

class GroupType(str, Enum):
    fixed = "fixed"
    dynamic = "dynamic"

class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, description="Group name")
    description: Optional[str] = Field(None, max_length=1024, description="Group description")
    group_type: GroupType = Field(description="Type of group (fixed or dynamic)")
    properties: Optional[dict] = Field(None, description="Additional group properties")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Group name cannot be empty or only whitespace')
        return v.strip()
    
    model_config = ConfigDict(use_enum_values=True)

class GroupGet(BaseEntityGet):
    id: str = Field(description="Group unique identifier")
    name: str = Field(description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    group_type: GroupType = Field(description="Type of group")
    properties: Optional[dict] = Field(None, description="Additional properties")
    
    @property
    def display_name(self) -> str:
        """Get display name for the group"""
        return self.name
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class GroupList(BaseEntityList):
    id: str = Field(description="Group unique identifier")
    name: str = Field(description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    group_type: GroupType = Field(description="Type of group")
    
    @property
    def display_name(self) -> str:
        """Get display name for lists"""
        return self.name
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Group name")
    description: Optional[str] = Field(None, max_length=1024, description="Group description")
    group_type: Optional[GroupType] = Field(None, description="Type of group")
    properties: Optional[dict] = Field(None, description="Additional properties")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Group name cannot be empty or only whitespace')
        return v.strip() if v else v
    
    model_config = ConfigDict(use_enum_values=True)

class GroupQuery(ListQuery):
    id: Optional[str] = Field(None, description="Filter by group ID")
    name: Optional[str] = Field(None, description="Filter by group name")
    group_type: Optional[GroupType] = Field(None, description="Filter by group type")
    archived: Optional[bool] = Field(None, description="Filter by archived status")
    
    model_config = ConfigDict(use_enum_values=True)


class GroupInterface(EntityInterface):
    create = GroupCreate
    get = GroupGet
    list = GroupList
    update = GroupUpdate
    query = GroupQuery
