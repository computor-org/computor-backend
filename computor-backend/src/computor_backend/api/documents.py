"""Documents API — write side.

Read access is served by the ``static-server`` container at ``/docs``;
this router only handles writes (file upload, file delete, mkdir,
rmdir). Each request carries its scope (system, organization,
course_family, course) and the relative path inside that scope's
documents area.
"""
import logging
import shutil
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from computor_backend.business_logic.documents import (
    check_documents_write_permission,
    check_reserved_name_collision,
    resolve_absolute_path,
    resolve_scope_root,
    validate_relative_path,
    DocumentScope,
)
from computor_backend.database import get_db
from computor_backend.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.settings import settings
from computor_types.documents import (
    DocumentCreate,
    DocumentDelete,
    DocumentDirectoryCreate,
    DocumentDirectoryDelete,
    DocumentDirectoryGet,
    DocumentGet,
)


logger = logging.getLogger(__name__)
documents_router = APIRouter(prefix="/documents", tags=["documents"])


_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB — read in chunks so a malicious
                                  # client can't OOM us with a huge body
                                  # before we hit the configured limit.


async def _read_upload_with_limit(file: UploadFile, max_bytes: int) -> bytes:
    """Read an ``UploadFile`` in chunks, aborting if it exceeds ``max_bytes``.

    Reading in chunks avoids buffering an unbounded amount in memory if a
    client lies about the body size (or doesn't set Content-Length).
    """
    parts: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise BadRequestException(
                detail=f"File exceeds the {max_bytes}-byte limit",
                context={"limit": max_bytes},
            )
        parts.append(chunk)
    return b"".join(parts)


@documents_router.post(
    "/files",
    response_model=DocumentGet,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_file(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    scope: Annotated[DocumentScope, Form()],
    path: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    scope_id: Annotated[Optional[UUID], Form()] = None,
    db: Session = Depends(get_db),
) -> DocumentGet:
    """Create or overwrite a documents file at the given scope and path."""
    payload = DocumentCreate(scope=scope, scope_id=scope_id, path=path)

    check_documents_write_permission(permissions, payload.scope, payload.scope_id)
    segments = validate_relative_path(payload.path)
    check_reserved_name_collision(payload.scope, payload.scope_id, segments[0], db)

    scope_root = resolve_scope_root(payload.scope, payload.scope_id, db)
    target = resolve_absolute_path(scope_root, segments)

    if target.is_dir():
        raise ConflictException(
            detail="A directory exists at the target path",
            context={"path": payload.path},
        )

    content = await _read_upload_with_limit(file, settings.DOCUMENTS_MAX_FILE_SIZE)

    # Atomic write: write to a sibling tmp file then rename, so the
    # static-server never sees half-written content.
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_bytes(content)
    tmp.replace(target)

    logger.info(
        "Uploaded document %s (scope=%s scope_id=%s size=%d)",
        payload.path, payload.scope, payload.scope_id, len(content),
    )

    return DocumentGet(
        scope=payload.scope,
        scope_id=payload.scope_id,
        path=payload.path,
        size=len(content),
        content_type=file.content_type,
    )


@documents_router.delete("/files", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_file(
    payload: DocumentDelete,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> None:
    """Delete a documents file."""
    check_documents_write_permission(permissions, payload.scope, payload.scope_id)
    segments = validate_relative_path(payload.path)
    check_reserved_name_collision(payload.scope, payload.scope_id, segments[0], db)

    scope_root = resolve_scope_root(payload.scope, payload.scope_id, db)
    target = resolve_absolute_path(scope_root, segments)

    if not target.exists():
        raise NotFoundException(
            detail="File not found",
            context={"path": payload.path},
        )
    if not target.is_file():
        raise ConflictException(
            detail="Target is not a file; use the directory endpoints",
            context={"path": payload.path},
        )

    target.unlink()
    logger.info(
        "Deleted document %s (scope=%s scope_id=%s)",
        payload.path, payload.scope, payload.scope_id,
    )


@documents_router.post(
    "/directories",
    response_model=DocumentDirectoryGet,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_directory(
    payload: DocumentDirectoryCreate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> DocumentDirectoryGet:
    """Create a documents directory (idempotent — returns ``created=False``
    when it already existed).
    """
    check_documents_write_permission(permissions, payload.scope, payload.scope_id)
    segments = validate_relative_path(payload.path)
    check_reserved_name_collision(payload.scope, payload.scope_id, segments[0], db)

    scope_root = resolve_scope_root(payload.scope, payload.scope_id, db)
    target = resolve_absolute_path(scope_root, segments)

    if target.exists():
        if target.is_dir():
            return DocumentDirectoryGet(
                scope=payload.scope,
                scope_id=payload.scope_id,
                path=payload.path,
                created=False,
            )
        raise ConflictException(
            detail="A file exists at the target path",
            context={"path": payload.path},
        )

    target.mkdir(parents=True, exist_ok=False)
    logger.info(
        "Created documents directory %s (scope=%s scope_id=%s)",
        payload.path, payload.scope, payload.scope_id,
    )
    return DocumentDirectoryGet(
        scope=payload.scope,
        scope_id=payload.scope_id,
        path=payload.path,
        created=True,
    )


@documents_router.delete("/directories", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_directory(
    payload: DocumentDirectoryDelete,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> None:
    """Delete a documents directory recursively.

    Refuses (409) when the leading segment matches an entity's path —
    those directories are entity-bound and can only be removed via
    entity deletion.
    """
    check_documents_write_permission(permissions, payload.scope, payload.scope_id)
    segments = validate_relative_path(payload.path)
    check_reserved_name_collision(payload.scope, payload.scope_id, segments[0], db)

    scope_root = resolve_scope_root(payload.scope, payload.scope_id, db)
    target = resolve_absolute_path(scope_root, segments)

    if not target.exists():
        raise NotFoundException(
            detail="Directory not found",
            context={"path": payload.path},
        )
    if not target.is_dir():
        raise ConflictException(
            detail="Target is not a directory; use the file endpoints",
            context={"path": payload.path},
        )

    shutil.rmtree(target)
    logger.info(
        "Deleted documents directory %s (scope=%s scope_id=%s)",
        payload.path, payload.scope, payload.scope_id,
    )
