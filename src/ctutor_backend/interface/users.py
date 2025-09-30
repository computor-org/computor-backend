from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.orm import Session
from text_unidecode import unidecode
from ctutor_backend.interface.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery
from ctutor_backend.interface.student_profile import StudentProfileGet
from ctutor_backend.model.auth import User

# Forward reference for ProfileGet to avoid circular import
if TYPE_CHECKING:
    from ctutor_backend.interface.profiles import ProfileGet

class UserTypeEnum(str, Enum):
    user = "user"
    token = "token"

class UserCreate(BaseModel):
    id: Optional[str] = Field(None, description="User ID (UUID will be generated if not provided)")
    given_name: Optional[str] = Field(None, min_length=1, max_length=255, description="User's given name")
    family_name: Optional[str] = Field(None, min_length=1, max_length=255, description="User's family name")
    email: Optional[str] = Field(None, description="User's email address")
    number: Optional[str] = Field(None, min_length=1, max_length=255, description="User number/identifier")
    user_type: Optional[UserTypeEnum] = Field(UserTypeEnum.user, description="Type of user account")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Unique username")
    properties: Optional[dict] = Field(None, description="Additional user properties")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is None:
            return v
        # Basic email validation
        if not v:
            raise ValueError('Email cannot be empty')
        if '@' not in v:
            raise ValueError('Email must contain @ symbol')
        # Check for basic structure: something@something
        parts = v.split('@')
        if len(parts) != 2:
            raise ValueError('Email must have exactly one @ symbol')
        local, domain = parts
        if not local:
            raise ValueError('Email must have local part before @')
        if not domain:
            raise ValueError('Email must have domain after @')
        # Check for spaces
        if ' ' in v:
            raise ValueError('Email cannot contain spaces')
        # Check for consecutive dots
        if '..' in v:
            raise ValueError('Email cannot contain consecutive dots')
        return v


    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if v is not None:
            if not v.replace('_', '').replace('-', '').replace('.', '').isalnum():
                raise ValueError('Username can only contain alphanumeric characters, underscores, hyphens, and dots')
        return v
    
    @field_validator('given_name', 'family_name')
    @classmethod
    def validate_names(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty or only whitespace')
        return v.strip() if v else v
    
    model_config = ConfigDict(use_enum_values=True)

class UserGet(BaseEntityGet):
    id: str = Field(description="User unique identifier")
    given_name: Optional[str] = Field(None, description="User's given name")
    family_name: Optional[str] = Field(None, description="User's family name")
    email: Optional[str] = Field(None, description="User's email address")
    number: Optional[str] = Field(None, description="User number/identifier")
    user_type: Optional[UserTypeEnum] = Field(None, description="Type of user account")
    username: Optional[str] = Field(None, description="Unique username")
    properties: Optional[dict] = Field(None, description="Additional user properties")
    archived_at: Optional[datetime] = Field(None, description="Timestamp when user was archived")
    student_profiles: List[StudentProfileGet] = Field(default=[], description="Associated student profiles")
    profile: Optional['ProfileGet'] = Field(None, description="User profile")
    
    
    @property
    def full_name(self) -> str:
        """Get the user's full name"""
        parts = []
        if self.given_name:
            parts.append(self.given_name)
        if self.family_name:
            parts.append(self.family_name)
        return ' '.join(parts) if parts else ''
    
    @property
    def display_name(self) -> str:
        """Get the user's display name (full name or username)"""
        full_name = self.full_name
        return full_name if full_name else (self.username or f"User {self.id[:8]}")
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class UserList(BaseEntityList):
    id: str = Field(description="User unique identifier")
    given_name: Optional[str] = Field(None, description="User's given name")
    family_name: Optional[str] = Field(None, description="User's family name")
    email: Optional[str] = Field(None, description="User's email address")
    user_type: Optional[UserTypeEnum] = Field(None, description="Type of user account")
    username: Optional[str] = Field(None, description="Unique username")
    archived_at: Optional[datetime] = Field(None, description="Archive timestamp")
    
    
    @property
    def display_name(self) -> str:
        """Get the user's display name for lists"""
        if self.given_name and self.family_name:
            return f"{self.given_name} {self.family_name}"
        elif self.given_name:
            return self.given_name
        elif self.username:
            return self.username
        return f"User {self.id[:8]}"
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class UserUpdate(BaseModel):
    given_name: Optional[str] = Field(None, min_length=1, max_length=255, description="User's given name")
    family_name: Optional[str] = Field(None, min_length=1, max_length=255, description="User's family name")
    email: Optional[str] = Field(None, description="User's email address")
    number: Optional[str] = Field(None, min_length=1, max_length=255, description="User number/identifier")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Unique username")
    properties: Optional[dict] = Field(None, description="Additional user properties")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is None:
            return v
        # Basic email validation
        if not v:
            raise ValueError('Email cannot be empty')
        if '@' not in v:
            raise ValueError('Email must contain @ symbol')
        # Check for basic structure: something@something
        parts = v.split('@')
        if len(parts) != 2:
            raise ValueError('Email must have exactly one @ symbol')
        local, domain = parts
        if not local:
            raise ValueError('Email must have local part before @')
        if not domain:
            raise ValueError('Email must have domain after @')
        # Check for spaces
        if ' ' in v:
            raise ValueError('Email cannot contain spaces')
        # Check for consecutive dots
        if '..' in v:
            raise ValueError('Email cannot contain consecutive dots')
        return v
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if v is not None:
            if not v.replace('_', '').replace('-', '').replace('.', '').isalnum():
                raise ValueError('Username can only contain alphanumeric characters, underscores, hyphens, and dots')
        return v
    
    @field_validator('given_name', 'family_name')
    @classmethod
    def validate_names(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty or only whitespace')
        return v.strip() if v else v

class UserQuery(ListQuery):
    id: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    email: Optional[str] = None
    number: Optional[str] = None
    user_type: Optional[UserTypeEnum] = None
    properties: Optional[dict] = None
    archived: Optional[bool] = None
    username: Optional[str] = None

def user_search(db: Session, query, params: Optional[UserQuery]):

    if params.id != None:
        query = query.filter(User.id == params.id)
    if params.given_name != None:
        query = query.filter(User.given_name == params.given_name)
    if params.family_name != None:
        query = query.filter(User.family_name == params.family_name)
    if params.email != None:
        query = query.filter(User.email == params.email)
    if params.number != None:
        query = query.filter(User.number == params.number)
    if params.user_type != None:
        query = query.filter(User.user_type == params.user_type)
    if params.username != None:
        query = query.filter(User.username == params.username)
        
    if params.archived != None and params.archived != False:
        query = query.filter(User.archived_at != None)
    else:
        query = query.filter(User.archived_at == None)
    
    return query

class UserInterface(EntityInterface):
    create = UserCreate
    get = UserGet
    list = UserList
    update = UserUpdate
    query = UserQuery
    search = user_search
    endpoint = "users"
    model = User
    cache_ttl = 300  # 5 minutes cache for user data


# Import ProfileGet after UserGet is defined to avoid circular import
from ctutor_backend.interface.profiles import ProfileGet
# Rebuild the model to resolve forward references
UserGet.model_rebuild()


def replace_special_chars(name: str) -> str:
    return unidecode(name.lower().replace("ö","oe").replace("ä","ae").replace("ü","ue").encode().decode("utf8"))

def gitlab_project_path(user: UserGet | UserList):
    first_name = replace_special_chars(user.given_name).replace(" ", "_")
    family_name = replace_special_chars(user.family_name).replace(" ", "_")

    return f"{family_name}_{first_name}"