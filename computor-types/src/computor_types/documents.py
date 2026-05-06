"""DTOs for the Documents API.

The API is write-only — reads are served by the ``static-server``
container at ``/docs``. Each request carries the scope (system,
organization, course_family, course) and the relative path inside
that scope's documents area.
"""
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


DocumentScopeName = Literal["system", "organization", "course_family", "course"]


class _DocumentScopedPathBase(BaseModel):
    """Shared fields and validation for all documents-API payloads.

    Not exported — concrete request/response classes inherit from it so
    the per-endpoint type still follows the ``<Entity><Action>`` naming
    convention used elsewhere in this package.
    """
    scope: DocumentScopeName = Field(
        description="Documents scope. 'system' = top-level admin-only area; "
                    "others must be paired with the matching scope_id."
    )
    scope_id: Optional[UUID] = Field(
        default=None,
        description="Entity ID for the chosen scope. Required for "
                    "organization / course_family / course; ignored for system.",
    )
    path: str = Field(
        description="Relative path inside the scope's documents area. "
                    "Must not contain '..' or absolute components.",
        min_length=1,
    )

    @model_validator(mode="after")
    def _scope_id_required_unless_system(self) -> "_DocumentScopedPathBase":
        if self.scope != "system" and self.scope_id is None:
            raise ValueError("scope_id is required for non-system scopes")
        return self


class DocumentCreate(_DocumentScopedPathBase):
    """Form fields for ``POST /documents/files`` (the file itself is
    sent as a multipart upload alongside this payload).
    """


class DocumentDelete(_DocumentScopedPathBase):
    """Body for ``DELETE /documents/files``."""


class DocumentGet(BaseModel):
    """Response from a successful file upload."""
    scope: DocumentScopeName
    scope_id: Optional[UUID] = None
    path: str
    size: int = Field(description="File size in bytes after writing.")
    content_type: Optional[str] = None


class DocumentDirectoryCreate(_DocumentScopedPathBase):
    """Body for ``POST /documents/directories``."""


class DocumentDirectoryDelete(_DocumentScopedPathBase):
    """Body for ``DELETE /documents/directories``."""


class DocumentDirectoryGet(BaseModel):
    """Response from a successful mkdir."""
    scope: DocumentScopeName
    scope_id: Optional[UUID] = None
    path: str
    created: bool = Field(description="False if the directory already existed.")
