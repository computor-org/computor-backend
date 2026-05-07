"""Documents API.

Public read access is served by the ``static-server`` container at
``/docs``. This router covers writes (file upload, file delete, mkdir,
rmdir, rename) plus authenticated GETs (list a directory, fetch a
file) for callers that already hold a session — VS Code extension,
admin scripts, etc. Each request carries its scope (system,
organization, course_family, course) and the relative path inside
that scope's documents area.
"""
import logging
import os
import shutil
from datetime import datetime, timezone
from email.utils import formatdate
from typing import Annotated, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from computor_backend.business_logic.documents import (
    check_documents_write_permission,
    check_reserved_name_collision,
    resolve_absolute_path,
    resolve_listing_target,
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
    DocumentDirectoryRename,
    DocumentGet,
    DocumentList,
    DocumentRename,
)


logger = logging.getLogger(__name__)
documents_router = APIRouter(prefix="/documents", tags=["documents"])


_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB — read in chunks so a malicious
                                  # client can't OOM us with a huge body
                                  # before we hit the configured limit.


def _stat_etag(stat: os.stat_result) -> str:
    """Quoted ETag derived from mtime+size.

    Same format Starlette's ``FileResponse`` uses by default, so the
    values returned by the listing endpoint match the ``ETag`` header
    the file GET endpoint emits — clients can compare without
    normalizing.
    """
    return f'"{stat.st_mtime}-{stat.st_size}"'


def _if_none_match_hits(header: str, etag: str) -> bool:
    """Compare a client's ``If-None-Match`` header against ``etag``.

    Accepts a comma-separated list and the wildcard ``*``; ``W/``
    weak prefixes on either side are stripped before comparison so a
    client that re-quotes the etag as weak still matches.
    """
    def normalize(s: str) -> str:
        s = s.strip()
        if s.startswith("W/"):
            s = s[2:]
        return s

    target = normalize(etag)
    for raw in header.split(","):
        candidate = raw.strip()
        if candidate == "*":
            return True
        if normalize(candidate) == target:
            return True
    return False


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


@documents_router.patch("/files", response_model=DocumentGet)
async def rename_document_file(
    payload: DocumentRename,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> DocumentGet:
    """Rename a documents file inside the same scope.

    Source must exist and be a file; target must not exist. Both
    paths are validated. Atomic on the same filesystem (which is
    always true for ``DOCUMENTS_ROOT``).
    """
    check_documents_write_permission(permissions, payload.scope, payload.scope_id)
    src_segments = validate_relative_path(payload.path)
    dst_segments = validate_relative_path(payload.new_path)
    check_reserved_name_collision(payload.scope, payload.scope_id, src_segments[0], db)
    check_reserved_name_collision(payload.scope, payload.scope_id, dst_segments[0], db)

    scope_root = resolve_scope_root(payload.scope, payload.scope_id, db)
    src = resolve_absolute_path(scope_root, src_segments)
    dst = resolve_absolute_path(scope_root, dst_segments)

    if src == dst:
        raise BadRequestException(
            detail="Source and target paths are identical",
            context={"path": payload.path},
        )
    if not src.exists():
        raise NotFoundException(
            detail="File not found", context={"path": payload.path}
        )
    if not src.is_file():
        raise ConflictException(
            detail="Source is not a file; use the directory endpoint",
            context={"path": payload.path},
        )
    if dst.exists():
        raise ConflictException(
            detail="Target path already exists",
            context={"path": payload.new_path},
        )

    dst.parent.mkdir(parents=True, exist_ok=True)
    src.replace(dst)

    stat = dst.stat()
    logger.info(
        "Renamed documents file %s -> %s (scope=%s scope_id=%s)",
        payload.path, payload.new_path, payload.scope, payload.scope_id,
    )
    return DocumentGet(
        scope=payload.scope,
        scope_id=payload.scope_id,
        path=payload.new_path,
        size=stat.st_size,
        content_type=None,
    )


@documents_router.patch("/directories", response_model=DocumentDirectoryGet)
async def rename_document_directory(
    payload: DocumentDirectoryRename,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> DocumentDirectoryGet:
    """Rename a documents directory inside the same scope.

    Source must exist and be a directory; target must not exist;
    target must not lie inside the source (no moving a dir into
    itself). ``created`` in the response is always ``False`` — the
    directory was moved, not freshly created.
    """
    check_documents_write_permission(permissions, payload.scope, payload.scope_id)
    src_segments = validate_relative_path(payload.path)
    dst_segments = validate_relative_path(payload.new_path)
    check_reserved_name_collision(payload.scope, payload.scope_id, src_segments[0], db)
    check_reserved_name_collision(payload.scope, payload.scope_id, dst_segments[0], db)

    scope_root = resolve_scope_root(payload.scope, payload.scope_id, db)
    src = resolve_absolute_path(scope_root, src_segments)
    dst = resolve_absolute_path(scope_root, dst_segments)

    if src == dst:
        raise BadRequestException(
            detail="Source and target paths are identical",
            context={"path": payload.path},
        )
    if dst.is_relative_to(src):
        raise BadRequestException(
            detail="Cannot move a directory into itself",
            context={"path": payload.path, "new_path": payload.new_path},
        )
    if not src.exists():
        raise NotFoundException(
            detail="Directory not found", context={"path": payload.path}
        )
    if not src.is_dir():
        raise ConflictException(
            detail="Source is not a directory; use the file endpoint",
            context={"path": payload.path},
        )
    if dst.exists():
        raise ConflictException(
            detail="Target path already exists",
            context={"path": payload.new_path},
        )

    dst.parent.mkdir(parents=True, exist_ok=True)
    src.replace(dst)

    logger.info(
        "Renamed documents directory %s -> %s (scope=%s scope_id=%s)",
        payload.path, payload.new_path, payload.scope, payload.scope_id,
    )
    return DocumentDirectoryGet(
        scope=payload.scope,
        scope_id=payload.scope_id,
        path=payload.new_path,
        created=False,
    )


@documents_router.get("/list", response_model=list[DocumentList])
async def list_documents_directory(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    scope: Annotated[DocumentScope, Query()],
    scope_id: Annotated[Optional[UUID], Query()] = None,
    path: Annotated[Optional[str], Query()] = None,
    db: Session = Depends(get_db),
) -> list[DocumentList]:
    """List entries in a documents directory.

    Available to any authenticated user. An unwritten scope root
    returns an empty list (so a fresh course/family/org does not 404);
    a missing non-root path is a 404.
    """
    target = resolve_listing_target(scope, scope_id, path, db)

    if not target.exists():
        if not path:
            return []
        raise NotFoundException(
            detail="Directory not found", context={"path": path}
        )
    if not target.is_dir():
        raise ConflictException(
            detail="Target is not a directory", context={"path": path}
        )

    entries: list[DocumentList] = []
    for child in sorted(target.iterdir(), key=lambda p: p.name):
        # Skip symlinks (and broken ones) — writes refuse to create
        # them, and following them would defeat the scope-root
        # containment guarantee from resolve_absolute_path.
        if child.is_symlink():
            continue
        try:
            stat = child.stat()
        except OSError:
            continue
        last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        etag = _stat_etag(stat)
        if child.is_dir():
            entries.append(
                DocumentList(
                    name=child.name,
                    type="directory",
                    etag=etag,
                    last_modified=last_modified,
                )
            )
        elif child.is_file():
            entries.append(
                DocumentList(
                    name=child.name,
                    type="file",
                    size=stat.st_size,
                    etag=etag,
                    last_modified=last_modified,
                )
            )

    return entries


@documents_router.get("/files", response_class=FileResponse)
async def get_document_file(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    scope: Annotated[DocumentScope, Query()],
    path: Annotated[str, Query()],
    scope_id: Annotated[Optional[UUID], Query()] = None,
    if_none_match: Annotated[Optional[str], Header(alias="if-none-match")] = None,
    db: Session = Depends(get_db),
) -> Response:
    """Fetch a documents file. Available to any authenticated user.

    The same content is reachable unauthenticated via the static-server
    at ``/docs/<...>``; this endpoint serves authenticated callers
    through the same auth chain they use for everything else.

    Supports ``If-None-Match`` for cheap revalidation: when the
    supplied ETag matches the current file, returns ``304 Not
    Modified`` with the same ``ETag`` and ``Last-Modified`` headers
    the 200 response would carry.
    """
    segments = validate_relative_path(path)
    scope_root = resolve_scope_root(scope, scope_id, db)
    target = resolve_absolute_path(scope_root, segments)

    if not target.exists():
        raise NotFoundException(detail="File not found", context={"path": path})
    if not target.is_file():
        raise ConflictException(
            detail="Target is not a file", context={"path": path}
        )

    stat = target.stat()
    etag = _stat_etag(stat)
    last_modified = formatdate(stat.st_mtime, usegmt=True)
    cache_headers = {"ETag": etag, "Last-Modified": last_modified}

    if if_none_match and _if_none_match_hits(if_none_match, etag):
        return Response(status_code=304, headers=cache_headers)

    return FileResponse(
        path=str(target),
        filename=target.name,
        headers=cache_headers,
    )
