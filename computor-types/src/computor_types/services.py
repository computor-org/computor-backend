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
                      description=(
                          "URL-safe slug identifier (lowercase, alphanumeric, dots, hyphens). "
                          "For testing services this MUST match the "
                          "properties.executionBackend.slug your examples declare in meta.yaml"
                      ))
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable service name")
    description: Optional[str] = Field(None, description="Service description")
    service_type: str = Field(..., min_length=1, max_length=63,
                             description="ServiceType path, e.g. 'testing.temporal' or 'agent'")
    email: Optional[str] = Field(None, description="Email for service user")
    given_name: Optional[str] = Field(None, max_length=255, description="Given name for service user (defaults to first word of name)")
    family_name: Optional[str] = Field(None, max_length=255, description="Family name for service user (defaults to rest of name)")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Service-specific configuration")
    language: Optional[str] = Field(
        None,
        description=(
            "Test runner language for testing services (python, octave, r, julia, "
            "c, cpp, fortran, document, matlab). Stored into config.language, which "
            "is what selects the runner — the slug never does. Required when the "
            "service type's category is 'testing'."
        ),
    )
    enabled: Optional[bool] = Field(True, description="Whether the service is enabled")


class ServiceUpdate(BaseModel):
    """DTO for updating a service account."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    config: Optional[Dict[str, Any]] = Field(None)
    language: Optional[str] = Field(
        None,
        description="Test runner language; merged into config.language.",
    )
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
    service_type_path: Optional[str] = Field(None, description="ServiceType path (e.g., 'testing.python')")
    user_id: str
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool
    last_seen_at: Optional[datetime] = None
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")


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
    endpoint_base = "/service-accounts"

    create = ServiceCreate
    update = ServiceUpdate
    get = ServiceGet
    list = ServiceList
    query = ServiceQuery
