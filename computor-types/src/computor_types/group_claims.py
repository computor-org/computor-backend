from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

class GroupClaimCreate(BaseModel):
    group_id: str = Field(description="Group ID this claim belongs to")
    claim_type: str = Field(min_length=1, max_length=255, description="Type of claim (e.g., 'permission', 'attribute')")
    claim_value: str = Field(min_length=1, max_length=255, description="Value of the claim")
    properties: Optional[dict] = Field(None, description="Additional claim properties")
    
    @field_validator('claim_type')
    @classmethod
    def validate_claim_type(cls, v):
        if not v.strip():
            raise ValueError('Claim type cannot be empty or only whitespace')
        # Normalize claim type to lowercase and standardize plural form for permissions
        lowered = v.strip().lower()
        return 'permissions' if lowered == 'permission' else lowered
    
    @field_validator('claim_value')
    @classmethod
    def validate_claim_value(cls, v):
        if not v.strip():
            raise ValueError('Claim value cannot be empty or only whitespace')
        return v.strip()

class GroupClaimGet(BaseEntityGet):
    group_id: str = Field(description="Group ID")
    claim_type: str = Field(description="Type of claim")
    claim_value: str = Field(description="Value of the claim")
    properties: Optional[dict] = Field(None, description="Additional properties")
    
    @property
    def display_name(self) -> str:
        """Get display name for the claim"""
        return f"{self.claim_type}: {self.claim_value}"
    
    @property
    def claim_identifier(self) -> str:
        """Get unique identifier for this claim"""
        return f"{self.group_id}:{self.claim_type}:{self.claim_value}"
    
    model_config = ConfigDict(from_attributes=True)

class GroupClaimList(BaseEntityList):
    group_id: str = Field(description="Group ID")
    claim_type: str = Field(description="Type of claim")
    claim_value: str = Field(description="Value of the claim")
    
    @property
    def display_name(self) -> str:
        """Get display name for lists"""
        return f"{self.claim_type}: {self.claim_value}"
    
    model_config = ConfigDict(from_attributes=True)

class GroupClaimUpdate(BaseModel):
    properties: Optional[dict] = Field(None, description="Additional claim properties")
    
    # Note: group_id, claim_type, and claim_value are part of composite primary key
    # and typically should not be updated. Only properties can be modified.

class GroupClaimQuery(ListQuery):
    group_id: Optional[str] = Field(None, description="Filter by group ID")
    claim_type: Optional[str] = Field(None, description="Filter by claim type")
    claim_value: Optional[str] = Field(None, description="Filter by claim value")

def group_claim_search(db: 'Session', query, params: Optional[GroupClaimQuery]):
    if params.group_id is not None:
        query = query.filter(group_id == params.group_id)
    if params.claim_type is not None:
        query = query.filter(claim_type == params.claim_type)
    if params.claim_value is not None:
        query = query.filter(claim_value.ilike(f"%{params.claim_value}%"))
    
    return query

class GroupClaimInterface(EntityInterface):
    create = GroupClaimCreate
    get = GroupClaimGet
    list = GroupClaimList
    update = GroupClaimUpdate
    query = GroupClaimQuery
    search = group_claim_search
    endpoint = "group-claims"
    model = None  # Set by backend
    cache_ttl = 180  # 3 minutes cache for claims (moderate change frequency)
