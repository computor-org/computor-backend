"""
Service DTOs for service account management.
"""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional, Dict, Any

from computor_types.base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery


RunnerBackend = Literal["local", "docker"]


class ServiceRunnerConfig(BaseModel):
    """Per-service runner configuration for student-code execution.

    Lives under ``Service.config["runner"]`` and is read by the
    ``ComputorTestingBackend`` when spawning ``computor-test``. ``local``
    executes student code in a host subprocess (the testing-worker
    container's namespace). ``docker`` spawns a fresh ``ct-sandbox`` /
    similar container per test, with hardening flags applied by the
    DockerRunner in ``computor-testing/sandbox/backends.py``.

    Validated by ``ServiceType.schema`` on the testing service-type rows;
    UI/API rejects writes that don't match this shape.
    """

    model_config = ConfigDict(extra="forbid")

    backend: RunnerBackend = Field(
        "local",
        description=(
            "Execution backend. ``local`` runs in the worker's own "
            "namespace; ``docker`` spawns a fresh container per test."
        ),
    )
    docker_image: Optional[str] = Field(
        None,
        description=(
            "Container image used when ``backend=docker`` "
            "(e.g. ``ct-sandbox:python``). Required if backend is docker."
        ),
    )
    timeout_seconds: Optional[float] = Field(
        None,
        gt=0,
        description="Per-test timeout in seconds. Falls back to executor defaults when null.",
    )
    memory_mb: Optional[int] = Field(
        None,
        gt=0,
        description="Memory cap (MiB) applied to the docker container. Ignored for local.",
    )
    cpus: Optional[float] = Field(
        None,
        gt=0,
        description="CPU quota for the docker container. Ignored for local.",
    )
    pids_limit: Optional[int] = Field(
        None,
        gt=0,
        description="Max number of PIDs inside the docker container. Ignored for local.",
    )
    network_enabled: Optional[bool] = Field(
        None,
        description=(
            "When false (the default for docker), the sandbox container "
            "is started with ``--network=none``."
        ),
    )


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
    given_name: Optional[str] = Field(None, max_length=255, description="Given name for service user (defaults to first word of name)")
    family_name: Optional[str] = Field(None, max_length=255, description="Family name for service user (defaults to rest of name)")
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
