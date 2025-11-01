from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional


    
from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

class GroupType(str, Enum):
    fixed = "fixed"
    dynamic = "dynamic"

class GroupCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255, description="Group title")
    slug: str = Field(min_length=1, max_length=255, description="Group slug identifier")
    description: Optional[str] = Field(None, max_length=4096, description="Group description")
    type: GroupType = Field(description="Type of group (fixed or dynamic)")
    properties: Optional[dict] = Field(None, description="Additional group properties")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Group title cannot be empty or only whitespace')
        return v.strip()

    model_config = ConfigDict(use_enum_values=True)

class GroupGet(BaseEntityGet):
    id: str = Field(description="Group unique identifier")
    title: str = Field(description="Group title")
    description: Optional[str] = Field(None, description="Group description")
    slug: str = Field(description="Group slug identifier")
    type: GroupType = Field(description="Type of group")
    properties: Optional[dict] = Field(None, description="Additional properties")

    @property
    def display_name(self) -> str:
        """Get display name for the group"""
        return self.title

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class GroupList(BaseEntityList):
    id: str = Field(description="Group unique identifier")
    title: str = Field(description="Group title")
    description: Optional[str] = Field(None, description="Group description")
    slug: str = Field(description="Group slug identifier")
    type: GroupType = Field(description="Type of group")

    @property
    def display_name(self) -> str:
        """Get display name for lists"""
        return self.title

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class GroupUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Group title")
    slug: Optional[str] = Field(None, min_length=1, max_length=255, description="Group slug identifier")
    description: Optional[str] = Field(None, max_length=4096, description="Group description")
    type: Optional[GroupType] = Field(None, description="Type of group")
    properties: Optional[dict] = Field(None, description="Additional properties")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Group title cannot be empty or only whitespace')
        return v.strip() if v else v

    model_config = ConfigDict(use_enum_values=True)

class GroupQuery(ListQuery):
    id: Optional[str] = Field(None, description="Filter by group ID")
    title: Optional[str] = Field(None, description="Filter by group title")
    slug: Optional[str] = Field(None, description="Filter by group slug")
    type: Optional[GroupType] = Field(None, description="Filter by group type")

    model_config = ConfigDict(use_enum_values=True)


class GroupInterface(EntityInterface):
    create = GroupCreate
    get = GroupGet
    list = GroupList
    update = GroupUpdate
    query = GroupQuery
