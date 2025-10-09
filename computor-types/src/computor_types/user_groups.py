from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional


    
from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

class UserGroupCreate(BaseModel):
    user_id: str = Field(description="User ID")
    group_id: str = Field(description="Group ID")
    transient: Optional[bool] = Field(False, description="Whether this is a transient membership")
    
    @field_validator('user_id', 'group_id')
    @classmethod
    def validate_ids(cls, v):
        if not v or not v.strip():
            raise ValueError('ID cannot be empty')
        return v.strip()

class UserGroupGet(BaseEntityGet):
    user_id: str = Field(description="User ID")
    group_id: str = Field(description="Group ID")
    transient: Optional[bool] = Field(None, description="Whether this is transient membership")
    
    @property
    def membership_type(self) -> str:
        """Get membership type description"""
        return "Transient" if self.transient else "Permanent"
    
    @property
    def membership_identifier(self) -> str:
        """Get unique identifier for this membership"""
        return f"{self.user_id}:{self.group_id}"
    
    model_config = ConfigDict(from_attributes=True)

class UserGroupList(BaseEntityList):
    user_id: str = Field(description="User ID")
    group_id: str = Field(description="Group ID")
    transient: Optional[bool] = Field(None, description="Whether this is transient membership")
    
    @property
    def membership_type(self) -> str:
        """Get membership type for lists"""
        return "Transient" if self.transient else "Permanent"
    
    model_config = ConfigDict(from_attributes=True)

class UserGroupUpdate(BaseModel):
    transient: Optional[bool] = Field(None, description="Whether this is transient membership")
    
    # Note: user_id and group_id are part of composite primary key
    # and typically should not be updated. Only transient flag can be modified.

class UserGroupQuery(ListQuery):
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    group_id: Optional[str] = Field(None, description="Filter by group ID")
    transient: Optional[bool] = Field(None, description="Filter by transient status")


class UserGroupInterface(EntityInterface):
    create = UserGroupCreate
    get = UserGroupGet
    list = UserGroupList
    update = UserGroupUpdate
    query = UserGroupQuery
