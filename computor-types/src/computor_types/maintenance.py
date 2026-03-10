"""
Maintenance mode DTOs.

Pydantic models for maintenance status, activation, and scheduling.
"""

from typing import Optional

from pydantic import BaseModel, Field


class MaintenanceStatusGet(BaseModel):
    """Current maintenance status."""
    active: bool = False
    message: str = ""
    activated_at: Optional[str] = None
    activated_by: Optional[str] = None
    activated_by_name: Optional[str] = None
    scheduled_at: Optional[str] = None
    scheduled_by: Optional[str] = None
    scheduled_by_name: Optional[str] = None


class MaintenanceActivate(BaseModel):
    """Activate maintenance mode."""
    message: str = Field(
        default="The system is undergoing scheduled maintenance.",
        description="Message shown to users",
    )
    notify_websocket: bool = Field(
        default=True,
        description="Broadcast maintenance notification via WebSocket",
    )


class MaintenanceSchedule(BaseModel):
    """Schedule future maintenance."""
    scheduled_at: str = Field(
        ..., description="ISO8601 datetime when maintenance will start"
    )
    message: str = Field(
        default="Scheduled maintenance is planned.",
        description="Message shown to users",
    )
    notify_websocket: bool = Field(
        default=True,
        description="Broadcast schedule notification via WebSocket",
    )
