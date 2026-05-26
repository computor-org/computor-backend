from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class InviteLinkCreate(BaseModel):
    email: Optional[str] = Field(None, description="If set, only this email may accept the invite")
    max_uses: int = Field(1, ge=1, le=100, description="Maximum number of times this invite can be used")
    expires_in_days: int = Field(7, ge=1, le=365, description="Number of days until the invite expires")
    roles: List[str] = Field(default_factory=list, description="Role IDs to assign to the user on acceptance")
    note: Optional[str] = Field(None, max_length=255, description="Admin label for this invite")


class InviteLinkGet(BaseModel):
    id: str
    token: str
    created_by: Optional[str] = None
    email: Optional[str] = None
    max_uses: int
    use_count: int
    expires_at: datetime
    roles: List[str] = []
    note: Optional[str] = None
    revoked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InviteLinkList(BaseModel):
    id: str
    token: str
    email: Optional[str] = None
    max_uses: int
    use_count: int
    expires_at: datetime
    roles: List[str] = []
    note: Optional[str] = None
    revoked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InviteLinkPublic(BaseModel):
    """Invite info visible to unauthenticated users (no token, no creator details)."""
    id: str
    email: Optional[str] = None  # null if no restriction, otherwise the restricted email
    roles: List[str] = []
    expires_at: datetime
    note: Optional[str] = None


class InviteAccept(BaseModel):
    given_name: str = Field(..., min_length=1, max_length=100)
    family_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., description="Required; must match invite restriction if set")
    password: str = Field(..., description="Password to set for Keycloak login (complexity enforced by Keycloak realm policy)")

    @field_validator('email')
    @classmethod
    def email_valid(cls, v: str) -> str:
        if '@' not in v or ' ' in v:
            raise ValueError("Invalid email address")
        return v.lower().strip()
