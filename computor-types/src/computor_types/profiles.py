from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

class ProfileCreate(BaseModel):
    user_id: str = Field(description="Associated user ID")
    avatar_color: Optional[int] = Field(None, ge=0, le=16777215, description="Avatar color as RGB integer (0-16777215)")
    avatar_image: Optional[str] = Field(None, max_length=2048, description="Avatar image URL")
    nickname: Optional[str] = Field(None, min_length=2, max_length=255, description="Unique nickname")
    bio: Optional[str] = Field(None, max_length=16384, description="User biography")
    url: Optional[str] = Field(None, max_length=2048, description="User website URL")
    language_code: Optional[str] = Field(None, max_length=2, description="ISO 639-1 language code")
    properties: Optional[dict] = Field(None, description="Additional profile properties")
    
    @field_validator('nickname')
    @classmethod
    def validate_nickname(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Nickname cannot be empty or only whitespace')
            # Nickname should only contain alphanumeric, underscore, hyphen
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError('Nickname can only contain alphanumeric characters, underscores, and hyphens')
        return v
    
    @field_validator('url', 'avatar_image')
    @classmethod
    def validate_urls(cls, v):
        if v:
            if not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError('URL must start with http:// or https://')
            # Check for incomplete URLs
            if v == 'http://' or v == 'https://':
                raise ValueError('URL must include a domain after the protocol')
        return v
    
    @field_validator('bio')
    @classmethod
    def validate_bio(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None  # Empty bio is allowed
        return v

class ProfileGet(BaseEntityGet):
    id: str = Field(description="Profile unique identifier")
    user_id: str = Field(description="Associated user ID")
    avatar_color: Optional[int] = Field(None, description="Avatar color as RGB integer")
    avatar_image: Optional[str] = Field(None, description="Avatar image URL")
    nickname: Optional[str] = Field(None, description="Unique nickname")
    bio: Optional[str] = Field(None, description="User biography")
    url: Optional[str] = Field(None, description="User website URL")
    language_code: Optional[str] = Field(None, description="ISO 639-1 language code")
    properties: Optional[dict] = Field(None, description="Additional properties")
    
    @property
    def display_name(self) -> str:
        """Get display name for the profile"""
        return self.nickname or f"Profile {self.id[:8]}"
    
    @property
    def avatar_color_hex(self) -> Optional[str]:
        """Get avatar color as hex string"""
        if self.avatar_color is not None:
            return f"#{self.avatar_color:06x}"
        return None
    
    @property
    def has_custom_avatar(self) -> bool:
        """Check if user has custom avatar image"""
        return bool(self.avatar_image)
    
    model_config = ConfigDict(from_attributes=True)

class ProfileList(BaseEntityList):
    id: str = Field(description="Profile unique identifier")
    user_id: str = Field(description="Associated user ID")
    nickname: Optional[str] = Field(None, description="Unique nickname")
    avatar_image: Optional[str] = Field(None, description="Avatar image URL")
    avatar_color: Optional[int] = Field(None, description="Avatar color")
    language_code: Optional[str] = Field(None, description="ISO 639-1 language code")
    
    @property
    def display_name(self) -> str:
        """Get display name for lists"""
        return self.nickname or f"Profile {self.id[:8]}"
    
    model_config = ConfigDict(from_attributes=True)

class ProfileUpdate(BaseModel):
    avatar_color: Optional[int] = Field(None, ge=0, le=16777215, description="Avatar color as RGB integer")
    avatar_image: Optional[str] = Field(None, max_length=2048, description="Avatar image URL")
    nickname: Optional[str] = Field(None, min_length=2, max_length=255, description="Unique nickname")
    bio: Optional[str] = Field(None, max_length=16384, description="User biography")
    url: Optional[str] = Field(None, max_length=2048, description="User website URL")
    language_code: Optional[str] = Field(None, max_length=2, description="ISO 639-1 language code")
    properties: Optional[dict] = Field(None, description="Additional properties")
    
    @field_validator('nickname')
    @classmethod
    def validate_nickname(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Nickname cannot be empty or only whitespace')
            if not v.replace('_', '').replace('-', '').isalnum():
                raise ValueError('Nickname can only contain alphanumeric characters, underscores, and hyphens')
        return v
    
    @field_validator('url', 'avatar_image')
    @classmethod
    def validate_urls(cls, v):
        if v:
            if not (v.startswith('http://') or v.startswith('https://')):
                raise ValueError('URL must start with http:// or https://')
            # Check for incomplete URLs
            if v == 'http://' or v == 'https://':
                raise ValueError('URL must include a domain after the protocol')
        return v

class ProfileQuery(ListQuery):
    id: Optional[str] = Field(None, description="Filter by profile ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    nickname: Optional[str] = Field(None, description="Filter by nickname")

def profile_search(db: 'Session', query, params: Optional[ProfileQuery]):
    if params.id is not None:
        query = query.filter(id == params.id)
    if params.user_id is not None:
        query = query.filter(user_id == params.user_id)
    if params.nickname is not None:
        query = query.filter(nickname.ilike(f"%{params.nickname}%"))
    
    return query

class ProfileInterface(EntityInterface):
    create = ProfileCreate
    get = ProfileGet
    list = ProfileList
    update = ProfileUpdate
    query = ProfileQuery
    search = profile_search
    endpoint = "profiles"
    model = None  # Set by backend
    cache_ttl = 300  # 5 minutes cache for profile data