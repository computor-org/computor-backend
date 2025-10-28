"""
API Token DTOs for token-based authentication.
"""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery


class ApiTokenCreate(BaseModel):
    """
    DTO for creating a new API token.

    The actual token value is generated server-side and returned once.
    Store it securely - it cannot be retrieved later!
    """
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable token name")
    description: Optional[str] = Field(None, description="Token description/purpose")
    user_id: str = Field(..., description="User ID that owns this token")
    scopes: List[str] = Field(default_factory=list, description="Token scopes (e.g., ['read:courses', 'write:results'])")
    expires_at: Optional[datetime] = Field(None, description="Token expiration date (null = never expires)")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")


class ApiTokenCreateResponse(BaseModel):
    """
    Response after creating an API token.

    IMPORTANT: The token field contains the actual token value.
    This is the ONLY time it will be visible - store it securely!
    """
    id: str = Field(..., description="Token ID")
    token: str = Field(..., description="The actual token value (STORE SECURELY - shown only once!)")
    name: str
    description: Optional[str] = None
    user_id: str
    token_prefix: str = Field(..., description="Token prefix for identification (e.g., 'ctp_a1b2c3d4')")
    scopes: List[str]
    expires_at: Optional[datetime] = None
    created_at: datetime


class ApiTokenUpdate(BaseModel):
    """DTO for updating an API token."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    scopes: Optional[List[str]] = Field(None)
    expires_at: Optional[datetime] = Field(None)
    properties: Optional[Dict[str, Any]] = Field(None)


class ApiTokenRevoke(BaseModel):
    """DTO for revoking an API token."""
    revocation_reason: Optional[str] = Field(None, max_length=1000, description="Reason for revocation")


class ApiTokenGet(BaseEntityGet):
    """
    DTO for retrieving an API token.

    Note: The actual token value is NEVER returned after creation.
    Only metadata and the prefix are available.
    """
    name: str
    description: Optional[str] = None
    user_id: str
    token_prefix: str = Field(..., description="First 12 characters for identification")
    scopes: List[str]
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = Field(default=0, description="Number of times this token has been used")
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None


class ApiTokenList(BaseEntityList):
    """DTO for listing API tokens."""
    items: list[ApiTokenGet]


class ApiTokenQuery(ListQuery):
    """DTO for querying API tokens."""
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    revoked: Optional[bool] = Field(None, description="Filter by revoked status (null = all, true = revoked, false = active)")
    expired: Optional[bool] = Field(None, description="Filter by expiration status")
    scopes: Optional[List[str]] = Field(None, description="Filter by required scopes (token must have all)")


class ApiTokenInterface(EntityInterface):
    """Entity interface for API Token API endpoints."""
    name = "api_tokens"
    endpoint_base = "/api-tokens"

    create = ApiTokenCreate
    update = ApiTokenUpdate
    get = ApiTokenGet
    list = ApiTokenList
    query = ApiTokenQuery
