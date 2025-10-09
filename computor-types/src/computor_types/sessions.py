from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

import ipaddress

class SessionCreate(BaseModel):
    user_id: str = Field(description="Associated user ID")
    session_id: str = Field(min_length=1, max_length=1024, description="Hashed session token")
    refresh_token_hash: Optional[bytes] = Field(None, description="Hashed refresh token (binary)")
    created_ip: str = Field(description="IP address at session creation")
    last_ip: Optional[str] = Field(None, description="Last seen IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    device_label: Optional[str] = Field(None, description="Human-readable device description")
    expires_at: Optional[datetime] = Field(None, description="Session expiration time")
    refresh_expires_at: Optional[datetime] = Field(None, description="Refresh token expiration")
    properties: Optional[dict] = Field(default_factory=dict, description="Additional session properties")

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        if not v.strip():
            raise ValueError('Session ID cannot be empty or only whitespace')
        return v.strip()

    @field_validator('created_ip', 'last_ip')
    @classmethod
    def validate_ip_address(cls, v):
        if v is None:
            return v
        try:
            # This validates both IPv4 and IPv6 addresses
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')

class SessionGet(BaseEntityGet):
    id: str = Field(description="Session unique identifier")
    sid: str = Field(description="Unique session ID per device")
    user_id: str = Field(description="Associated user ID")
    session_id: str = Field(description="Hashed session token")
    created_at: datetime = Field(description="Session creation time")
    last_seen_at: Optional[datetime] = Field(None, description="Last activity time")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    revoked_at: Optional[datetime] = Field(None, description="Revocation timestamp")
    revocation_reason: Optional[str] = Field(None, description="Reason for revocation")
    ended_at: Optional[datetime] = Field(None, description="End timestamp (logout)")
    refresh_counter: int = Field(default=0, description="Number of token refreshes")
    created_ip: str = Field(description="IP at creation")
    last_ip: Optional[str] = Field(None, description="Last seen IP")
    device_label: Optional[str] = Field(None, description="Device description")
    properties: Optional[dict] = Field(None, description="Additional properties")

    # Legacy fields
    logout_time: Optional[datetime] = Field(None, description="Deprecated: use ended_at")
    ip_address: Optional[str] = Field(None, description="Deprecated: use created_ip")

    @property
    def is_active(self) -> bool:
        """Check if session is still active"""
        from datetime import datetime, timezone
        if self.revoked_at or self.ended_at:
            return False
        if self.expires_at and self.expires_at < datetime.now(timezone.utc):
            return False
        return True

    @property
    def session_duration(self) -> Optional[int]:
        """Get session duration in seconds (if ended)"""
        end_time = self.ended_at or self.logout_time
        if end_time and self.created_at:
            return int((end_time - self.created_at).total_seconds())
        return None

    @property
    def display_name(self) -> str:
        """Get display name for the session"""
        device = self.device_label or "Unknown Device"
        status = "Active" if self.is_active else "Ended"
        return f"{device} ({status})"

    model_config = ConfigDict(from_attributes=True)

class SessionList(BaseEntityList):
    id: str = Field(description="Session unique identifier")
    sid: str = Field(description="Unique session ID per device")
    user_id: str = Field(description="Associated user ID")
    session_id: str = Field(description="Hashed session token")
    created_at: datetime = Field(description="Session creation time")
    last_seen_at: Optional[datetime] = Field(None, description="Last activity time")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    revoked_at: Optional[datetime] = Field(None, description="Revocation timestamp")
    ended_at: Optional[datetime] = Field(None, description="End timestamp")
    created_ip: str = Field(description="IP at creation")
    last_ip: Optional[str] = Field(None, description="Last seen IP")
    device_label: Optional[str] = Field(None, description="Device description")
    refresh_counter: int = Field(default=0, description="Refresh count")

    # Legacy fields
    logout_time: Optional[datetime] = Field(None, description="Deprecated")
    ip_address: Optional[str] = Field(None, description="Deprecated")

    @property
    def is_active(self) -> bool:
        """Check if session is active"""
        from datetime import datetime, timezone
        if self.revoked_at or self.ended_at:
            return False
        if self.expires_at and self.expires_at < datetime.now(timezone.utc):
            return False
        return True

    @property
    def display_name(self) -> str:
        """Get display name for lists"""
        device = self.device_label or f"Session from {self.created_ip}"
        status = "Active" if self.is_active else "Ended"
        return f"{device} ({status})"

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
