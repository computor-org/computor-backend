"""Pydantic DTOs for the private VS Code extension registry."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict

from .base import EntityInterface

class ExtensionPublishRequest(BaseModel):
    """Form metadata submitted when publishing a new extension version."""

    version: Optional[str] = Field(
        None,
        description="Semantic version override (defaults to manifest value)",
    )
    engine_range: Optional[str] = Field(
        None,
        description="VS Code engine compatibility override",
    )
    display_name: Optional[str] = Field(
        None,
        description="Friendly display name for the extension",
    )
    description: Optional[str] = Field(
        None,
        description="Optional extension description",
    )

class ExtensionVersionBase(BaseModel):
    """Common fields describing an extension version."""

    version: str = Field(..., description="Semantic version identifier")
    version_number: int = Field(..., description="Sequential version number for ordering")
    engine_range: Optional[str] = Field(
        None,
        description="VS Code engine compatibility constraint",
    )
    yanked: bool = Field(False, description="Whether the version is yanked")
    size: int = Field(..., description="Package size in bytes")
    sha256: str = Field(..., description="SHA256 checksum of the VSIX contents")
    content_type: str = Field(..., description="Stored content type of the VSIX")
    created_at: datetime = Field(..., description="Creation timestamp")
    published_at: datetime = Field(..., description="Publish timestamp")

    model_config = ConfigDict(from_attributes=True)

class ExtensionVersionListItem(ExtensionVersionBase):
    """List view of extension versions."""

    model_config = ConfigDict(from_attributes=True)

class ExtensionVersionDetail(ExtensionVersionBase):
    """Detailed view of an extension version."""

    object_key: str = Field(..., description="Object storage key for the VSIX")

class ExtensionVersionListResponse(BaseModel):
    """Response payload for version listing."""

    items: List[ExtensionVersionListItem] = Field(default_factory=list)
    next_cursor: Optional[str] = Field(
        None,
        description="Pagination cursor for the next page, if available",
    )

class ExtensionMetadata(BaseModel):
    """Extension-level metadata including latest version information."""

    publisher: str = Field(..., description="Publisher identifier")
    name: str = Field(..., description="Extension name")
    display_name: Optional[str] = Field(
        None,
        description="Friendly display name for the extension",
    )
    description: Optional[str] = Field(
        None,
        description="Extension description",
    )
    id: str = Field(..., description="Database identifier for the extension")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    version_count: int = Field(..., description="Number of stored versions")
    latest_version: Optional[ExtensionVersionListItem] = Field(
        None,
        description="Metadata for the latest available version",
    )

    model_config = ConfigDict(from_attributes=True)

class ExtensionVersionYankRequest(BaseModel):
    """Request payload to (un)yank a specific version."""

    yanked: bool = Field(..., description="Target yank state for the version")

class ExtensionPublishResponse(ExtensionVersionDetail):
    """Response payload returned after publishing a version."""

    publisher: str = Field(..., description="Publisher identifier")
    name: str = Field(..., description="Extension name")

class ExtensionInterface(EntityInterface):
    """Interface definition for claim generation."""

    create = ExtensionPublishRequest
    get = ExtensionMetadata
    list = ExtensionVersionListItem
    update = ExtensionVersionYankRequest
