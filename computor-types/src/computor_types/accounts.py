from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
from datetime import datetime

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

class AccountCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=255, description="Authentication provider name")
    type: str = Field(description="Type of authentication account")
    provider_account_id: str = Field(min_length=1, max_length=255, description="Account ID from the provider")
    user_id: str = Field(description="Associated user ID")
    properties: Optional[dict] = Field(None, description="Provider-specific properties")
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        if not v.strip():
            raise ValueError('Provider cannot be empty')
        return v.strip().lower()
    
    @field_validator('provider_account_id')
    @classmethod
    def validate_provider_account_id(cls, v):
        if not v.strip():
            raise ValueError('Provider account ID cannot be empty')
        return v.strip()
    
    model_config = ConfigDict(use_enum_values=True)
    
class AccountGet(BaseEntityGet):
    id: str = Field(description="Account unique identifier")
    provider: str = Field(description="Authentication provider name")
    type: str = Field(description="Type of authentication account")
    provider_account_id: str = Field(description="Account ID from the provider")
    user_id: str = Field(description="Associated user ID")
    properties: Optional[dict] = Field(None, description="Provider-specific properties")
    
    @property
    def display_name(self) -> str:
        """Get display name for the account"""
        return f"{self.provider} ({self.type}): {self.provider_account_id}"
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class AccountList(BaseEntityList):
    id: str = Field(description="Account unique identifier")
    provider: str = Field(description="Authentication provider name")
    type: str = Field(description="Type of authentication account")
    provider_account_id: str = Field(description="Account ID from the provider")
    user_id: str = Field(description="Associated user ID")
    
    @property
    def display_name(self) -> str:
        """Get display name for lists"""
        return f"{self.provider} ({self.type})"
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    
class AccountUpdate(BaseModel):
    provider: Optional[str] = Field(None, min_length=1, max_length=255, description="Authentication provider name")
    type: Optional[str] = Field(None, description="Type of authentication account")
    provider_account_id: Optional[str] = Field(None, min_length=1, max_length=255, description="Account ID from the provider")
    properties: Optional[dict] = Field(None, description="Provider-specific properties")
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Provider cannot be empty')
        return v.strip().lower() if v else v
    
    @field_validator('provider_account_id')
    @classmethod
    def validate_provider_account_id(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Provider account ID cannot be empty')
        return v.strip() if v else v
    
    model_config = ConfigDict(use_enum_values=True)

class AccountQuery(ListQuery):
    id: Optional[str] = None
    provider: Optional[str] = None
    type: Optional[str] = None
    provider_account_id: Optional[str] = None
    user_id: Optional[str] = None
    properties: Optional[str] = None
    
def account_search(db: 'Session', query, params: Optional[AccountQuery]):
    if params is None:
        return query
        
    if params.id != None:
        query = query.filter(id == params.id)
    if params.provider != None:
        query = query.filter(provider == params.provider)
    if params.type != None:
        query = query.filter(type == params.type)
    if params.provider_account_id != None:
        query = query.filter(provider_account_id == params.provider_account_id)
    if params.user_id != None:
        query = query.filter(user_id == params.user_id)

    return query

class AccountInterface(EntityInterface):
    create = AccountCreate
    get = AccountGet
    list = AccountList
    update = AccountUpdate
    query = AccountQuery
    search = account_search
    endpoint = "accounts"
    model = None  # Set by backend
    cache_ttl = 180  # 3 minutes cache for account data