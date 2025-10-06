from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


    
from computor_types.base import EntityInterface, ListQuery

class RoleGet(BaseModel):
    id: str = Field(description="Role unique identifier")
    title: Optional[str] = Field(None, description="Role title")
    description: Optional[str] = Field(None, description="Role description")
    builtin: bool = Field(description="Whether this is a built-in role")
    
    @property
    def display_name(self) -> str:
        """Get display name for the role"""
        return self.title or f"Role {self.id[:8]}"
    
    @property
    def is_builtin(self) -> bool:
        """Check if this is a built-in role"""
        return self.builtin
    
    model_config = ConfigDict(from_attributes=True)

class RoleList(BaseModel):
    id: str = Field(description="Role unique identifier")
    title: Optional[str] = Field(None, description="Role title")
    builtin: bool = Field(description="Whether this is a built-in role")
    
    @property
    def display_name(self) -> str:
        """Get display name for lists"""
        return self.title or f"Role {self.id[:8]}"
    
    model_config = ConfigDict(from_attributes=True)
    
class RoleQuery(ListQuery):
    id: Optional[str] = Field(None, description="Filter by role ID")
    title: Optional[str] = Field(None, description="Filter by role title")
    description: Optional[str] = Field(None, description="Filter by description")
    builtin: Optional[bool] = Field(None, description="Filter by builtin status")


class RoleInterface(EntityInterface):
    create = None  # Roles are typically managed by system
    get = RoleGet
    list = RoleList
    update = None  # Roles are typically immutable
    query = RoleQuery
