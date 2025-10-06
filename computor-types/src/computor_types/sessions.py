from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

import ipaddress

class SessionCreate(BaseModel):
    user_id: str = Field(description="Associated user ID")
    session_id: str = Field(min_length=1, max_length=1024, description="Session identifier/token")
    ip_address: str = Field(description="IP address of the session")
    properties: Optional[dict] = Field(None, description="Additional session properties")
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v.strip():
            raise ValueError('Session ID cannot be empty or only whitespace')
        return v.strip()
    
    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v):
        try:
            # This validates both IPv4 and IPv6 addresses
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')

class SessionGet(BaseEntityGet):
    id: str = Field(description="Session unique identifier")
    user_id: str = Field(description="Associated user ID")
    session_id: str = Field(description="Session identifier/token")
    logout_time: Optional[datetime] = Field(None, description="Logout timestamp")
    ip_address: str = Field(description="IP address")
    properties: Optional[dict] = Field(None, description="Additional properties")
    
    @property
    def is_active(self) -> bool:
        """Check if session is still active"""
        return self.logout_time is None
    
    @property
    def session_duration(self) -> Optional[int]:
        """Get session duration in seconds (if logged out)"""
        if self.logout_time and self.created_at:
            return int((self.logout_time - self.created_at).total_seconds())
        return None
    
    @property
    def display_name(self) -> str:
        """Get display name for the session"""
        status = "Active" if self.is_active else "Logged out"
        return f"Session {self.session_id[:8]}... ({status})"
    
    model_config = ConfigDict(from_attributes=True)

class SessionList(BaseEntityList):
    id: str = Field(description="Session unique identifier")
    user_id: str = Field(description="Associated user ID")
    session_id: str = Field(description="Session identifier/token")
    logout_time: Optional[datetime] = Field(None, description="Logout timestamp")
    ip_address: str = Field(description="IP address")
    
    @property
    def is_active(self) -> bool:
        """Check if session is active"""
        return self.logout_time is None
    
    @property
    def display_name(self) -> str:
        """Get display name for lists"""
        status = "Active" if self.is_active else "Logged out"
        return f"Session from {self.ip_address} ({status})"
    
    model_config = ConfigDict(from_attributes=True)

class SessionUpdate(BaseModel):
    logout_time: Optional[datetime] = Field(None, description="Logout timestamp")
    properties: Optional[dict] = Field(None, description="Additional properties")
    
    # Note: session_id, user_id, and ip_address typically should not be updated
    # Only logout_time and properties are modifiable

class SessionQuery(ListQuery):
    id: Optional[str] = Field(None, description="Filter by session ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    session_id: Optional[str] = Field(None, description="Filter by session identifier")
    active_only: Optional[bool] = Field(None, description="Filter for active sessions only")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")

# BACKEND FUNCTION - Moved to backend in Phase 4
# def session_search(db: DBSession, query, params: Optional[SessionQuery]):
#     if params.id is not None:
#         query = query.filter(id == params.id)
#     if params.user_id is not None:
#         query = query.filter(user_id == params.user_id)
#     if params.session_id is not None:
#         query = query.filter(session_id.ilike(f"%{params.session_id}%"))
#     if params.ip_address is not None:
#         query = query.filter(ip_address == params.ip_address)
#
#     if params.active_only is not None and params.active_only:
#         query = query.filter(logout_time.is_(None))
#
#     return query
#
class SessionInterface(EntityInterface):
    create = SessionCreate
    get = SessionGet
    list = SessionList
    update = SessionUpdate
    query = SessionQuery
