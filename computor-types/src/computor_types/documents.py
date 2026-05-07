"""DTOs for the Documents API.

Public read access is served by the ``static-server`` container at
``/docs``. The API surface here covers writes (file upload, file
delete, mkdir, rmdir) plus authenticated GETs (list a directory, fetch
a file) for callers that already have a session — VS Code extension,
admin scripts, etc. Each request carries the scope (system,
organization, course_family, course) and the relative path inside that
scope's documents area.
"""
from datetime import datetime
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


class DocumentRename(_DocumentScopedPathBase):
    """Body for ``PATCH /documents/files`` (rename a file).

    ``path`` is the source; ``new_path`` is the target. Both validated
    against the same rules. The scope itself is unchanged — this is a
    same-scope rename, not a cross-scope move.
    """
    new_path: str = Field(
        description="Target relative path inside the scope's documents "
                    "area. Same validation rules as ``path``.",
        min_length=1,
    )


class DocumentDirectoryCreate(_DocumentScopedPathBase):
    """Body for ``POST /documents/directories``."""


class DocumentDirectoryDelete(_DocumentScopedPathBase):
    """Body for ``DELETE /documents/directories``."""


class DocumentDirectoryRename(_DocumentScopedPathBase):
    """Body for ``PATCH /documents/directories`` (rename a directory).

    Same shape as :class:`DocumentRename`. Refuses to move a directory
    into a path that lies inside itself.
    """
    new_path: str = Field(
        description="Target relative path inside the scope's documents "
                    "area. Same validation rules as ``path``.",
        min_length=1,
    )


class DocumentDirectoryGet(BaseModel):
    """Response from a successful mkdir."""
    scope: DocumentScopeName
    scope_id: Optional[UUID] = None
    path: str
    created: bool = Field(description="False if the directory already existed.")


class DocumentList(BaseModel):
    """One entry in a ``GET /documents/list`` response.

    A directory listing mixes files and subdirectories — ``type``
    discriminates, and ``size`` is null for directories. ``etag`` and
    ``last_modified`` are derived from the filesystem stat and let
    clients revalidate per entry against ``GET /documents/files`` via
    ``If-None-Match`` without a full re-download.
    """
    name: str
    type: Literal["file", "directory"]
    size: Optional[int] = Field(
        default=None,
        description="File size in bytes; null for directories.",
    )
    etag: str = Field(
        description="Quoted weak validator (matches the ETag the file "
                    "GET endpoint returns) for cache revalidation.",
    )
    last_modified: datetime = Field(description="UTC mtime of the entry.")
