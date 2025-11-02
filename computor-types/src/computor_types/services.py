"""
Service DTOs for service account management.
"""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery


class ServiceCreate(BaseModel):
    """DTO for creating a new service account."""
    slug: str = Field(..., min_length=3, max_length=255, pattern=r'^[a-z0-9][a-z0-9.\-]*[a-z0-9]$',
                      description="URL-safe slug identifier (lowercase, alphanumeric, dots, hyphens)")
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable service name")
    description: Optional[str] = Field(None, description="Service description")
    service_type: str = Field(..., min_length=1, max_length=63,
                             description="Service type (e.g., 'temporal_worker', 'grading', 'notification')")
    username: Optional[str] = Field(None, description="Username for service user (defaults to slug)")
    email: Optional[str] = Field(None, description="Email for service user")
    password: Optional[str] = Field(None, description="Password for service user (optional - use API tokens instead)")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Service-specific configuration")
    enabled: Optional[bool] = Field(True, description="Whether the service is enabled")


class ServiceUpdate(BaseModel):
    """DTO for updating a service account."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    config: Optional[Dict[str, Any]] = Field(None)
    enabled: Optional[bool] = Field(None)
    last_seen_at: Optional[datetime] = Field(None, description="Last heartbeat timestamp")
    properties: Optional[Dict[str, Any]] = Field(None)


class ServiceGet(BaseEntityGet):
    """DTO for retrieving a service account."""
    id: str = Field(..., description="Service UUID")
    slug: str
    name: str
    description: Optional[str] = None
    service_type_id: Optional[str] = Field(None, description="ServiceType UUID")
    user_id: str
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool
    last_seen_at: Optional[datetime] = None


class ServiceList(BaseEntityList):
    """DTO for listing services."""
    items: list[ServiceGet]


class ServiceQuery(ListQuery):
    """DTO for querying services."""
    id: Optional[str] = Field(None, description="Filter by service UUID")
    slug: Optional[str] = Field(None, description="Filter by service slug")
    service_type_id: Optional[str] = Field(None, description="Filter by service type UUID")
    enabled: Optional[bool] = Field(None, description="Filter by enabled status")
    user_id: Optional[str] = Field(None, description="Filter by user ID")


class ServiceInterface(EntityInterface):
    """Entity interface for Service API endpoints."""
    name = "services"
    endpoint_base = "/services"

    create = ServiceCreate
    update = ServiceUpdate
    get = ServiceGet
    list = ServiceList
    query = ServiceQuery
