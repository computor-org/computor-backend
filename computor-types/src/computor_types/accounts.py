from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
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
    

class AccountInterface(EntityInterface):
    create = AccountCreate
    get = AccountGet
    list = AccountList
    update = AccountUpdate
    query = AccountQuery
