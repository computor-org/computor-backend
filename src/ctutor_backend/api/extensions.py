"""FastAPI endpoints for the private VS Code extension registry."""

from __future__ import annotations

import base64
import hashlib
import io
import re
from datetime import datetime
from typing import Iterable, List, Optional, Tuple

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
)
from fastapi.responses import RedirectResponse
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..api.exceptions import BadRequestException, ForbiddenException, NotFoundException
from ..database import get_db
from ..interface.extensions import (
    ExtensionMetadata,
    ExtensionPublishRequest,
    ExtensionPublishResponse,
    ExtensionVersionDetail,
    ExtensionVersionListItem,
    ExtensionVersionListResponse,
    ExtensionVersionYankRequest,
)
from ..model.extension import Extension, ExtensionVersion
from ..permissions.auth import get_current_permissions
from ..permissions.principal import Principal
from ..services.storage_service import get_storage_service
from ..services.vsix_utils import VsixManifestError, parse_vsix_metadata

extensions_router = APIRouter(prefix="/extensions", tags=["extensions"])

_SEGMENT_SANITIZER = re.compile(r"[^A-Za-z0-9._-]+")


def _split_identity(identity: str) -> Tuple[str, str]:
    parts = identity.split(".", 1)
    if len(parts) != 2:
        raise BadRequestException("Extension path must be in 'publisher.name' format")
    publisher, name = parts[0].strip(), parts[1].strip()
    if not publisher or not name:
        raise BadRequestException("Extension publisher and name must be provided")
    return publisher, name


def _sanitize_segment(value: str) -> str:
    sanitized = _SEGMENT_SANITIZER.sub("-", value.strip().lower())
    sanitized = sanitized.strip("-")
    return sanitized or "unnamed"


def _generate_object_key(publisher: str, name: str, version: str, sha256: str) -> str:
    safe_publisher = _sanitize_segment(publisher)
    safe_name = _sanitize_segment(name)
    safe_version = _sanitize_segment(version)
    return f"extensions/{safe_publisher}/{safe_name}/{safe_version}/{sha256}.vsix"


def _parse_version(value: str) -> Version:
    try:
        return Version(value)
    except InvalidVersion as exc:
        raise BadRequestException(f"Invalid semantic version '{value}'") from exc


def _caret_to_specifier(base_version: str) -> SpecifierSet:
    parsed = _parse_version(base_version)
    lower = f">={base_version}"
    if parsed.major > 0:
        upper = f"<{parsed.major + 1}.0.0"
    elif parsed.minor > 0:
        upper = f"<0.{parsed.minor + 1}.0"
    else:
        upper = f"<0.0.{parsed.micro + 1}"
    return SpecifierSet(f"{lower},{upper}")


def _tilde_to_specifier(base_version: str) -> SpecifierSet:
    parsed = _parse_version(base_version)
    lower = f">={base_version}"
    upper_minor = parsed.minor + 1
    upper = f"<{parsed.major}.{upper_minor}.0"
    return SpecifierSet(f"{lower},{upper}")


def _coerce_specifier(value: str) -> Optional[SpecifierSet]:
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.lower() == "latest":
        return None
    if cleaned.startswith("^"):
        return _caret_to_specifier(cleaned[1:])
    if cleaned.startswith("~"):
        return _tilde_to_specifier(cleaned[1:])
    try:
        return SpecifierSet(cleaned)
    except InvalidSpecifier:
        return SpecifierSet(f"=={cleaned}")


def _encode_cursor(version_number: int) -> str:
    payload = str(version_number)
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8")


def _decode_cursor(cursor: str) -> int:
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        return int(decoded)
    except Exception as exc:  # noqa: BLE001
        raise BadRequestException("Invalid cursor token") from exc


def _get_extension_or_404(db: Session, publisher: str, name: str) -> Extension:
    extension = (
        db.query(Extension)
        .filter(Extension.publisher == publisher, Extension.name == name)
        .first()
    )
    if not extension:
        raise NotFoundException("Extension not found")
    return extension


def _get_or_create_extension(
    db: Session,
    publisher: str,
    name: str,
    display_name: Optional[str],
    description: Optional[str],
) -> Tuple[Extension, bool]:
    extension = (
        db.query(Extension)
        .filter(Extension.publisher == publisher, Extension.name == name)
        .first()
    )
    created = False
    if not extension:
        extension = Extension(
            publisher=publisher,
            name=name,
            display_name=display_name or name,
            description=description,
        )
        db.add(extension)
        created = True
    else:
        if display_name and extension.display_name != display_name:
            extension.display_name = display_name
        if description is not None and extension.description != description:
            extension.description = description
    return extension, created


def _select_version(
    versions: Iterable[ExtensionVersion],
    specifier: Optional[SpecifierSet],
) -> Optional[ExtensionVersion]:
    sorted_versions = sorted(
        ((Version(v.version), v) for v in versions),
        key=lambda item: item[0],
        reverse=True,
    )
    if specifier is None:
        return sorted_versions[0][1] if sorted_versions else None
    for parsed, version in sorted_versions:
        if parsed in specifier:
            return version
    return None


@extensions_router.post(
    "/{extension_identity}/versions",
    response_model=ExtensionPublishResponse,
    status_code=201,
)
async def publish_extension_version(
    extension_identity: str,
    version: Optional[str] = Form(None),
    engine_range: Optional[str] = Form(None),
    file: UploadFile = File(...),
    display_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    permissions: Principal = Depends(get_current_permissions),
    db: Session = Depends(get_db),
    storage_service=Depends(get_storage_service),
):
    if not permissions.permitted("extension", "create"):
        raise ForbiddenException("You don't have permission to publish extensions")

    publisher, name = _split_identity(extension_identity)

    publish_payload = ExtensionPublishRequest(
        version=version,
        engine_range=engine_range,
        display_name=display_name,
        description=description,
    )

    if not file.filename or not file.filename.lower().endswith(".vsix"):
        raise BadRequestException("Uploaded file must be a .vsix package")

    file_bytes = await file.read()
    if not file_bytes:
        raise BadRequestException("Uploaded VSIX file is empty")

    try:
        manifest = parse_vsix_metadata(file_bytes)
    except VsixManifestError as exc:
        raise BadRequestException(str(exc)) from exc

    target_version = publish_payload.version or manifest.version

    if publish_payload.version and manifest.version != publish_payload.version:
        raise BadRequestException(
            "Provided version does not match the VSIX manifest version"
        )

    if manifest.publisher.lower() != publisher.lower():
        raise BadRequestException(
            "Publisher in manifest does not match the requested extension path"
        )

    if manifest.name.lower() != name.lower():
        raise BadRequestException(
            "Extension identifier in manifest does not match the requested extension path"
        )

    parsed_version = _parse_version(target_version)
    prerelease = None
    if parsed_version.pre:
        identifier, number = parsed_version.pre
        prerelease = f"{identifier}{number if number is not None else ''}"

    resolved_display_name = publish_payload.display_name or manifest.display_name
    resolved_description = (
        publish_payload.description
        if publish_payload.description is not None
        else manifest.description
    )
    resolved_engine_range = publish_payload.engine_range or manifest.engine_range

    sha256 = hashlib.sha256(file_bytes).hexdigest()
    object_key = _generate_object_key(publisher, name, target_version, sha256)

    extension, created = _get_or_create_extension(
        db,
        publisher=publisher,
        name=name,
        display_name=resolved_display_name,
        description=resolved_description,
    )
    db.flush()  # ensure extension.id is available

    existing_version = (
        db.query(ExtensionVersion)
        .filter(
            ExtensionVersion.extension_id == extension.id,
            ExtensionVersion.version == target_version,
        )
        .first()
    )
    if existing_version:
        raise BadRequestException("Version already exists for this extension")

    max_version_number = (
        db.query(func.max(ExtensionVersion.version_number))
        .filter(ExtensionVersion.extension_id == extension.id)
        .scalar()
    ) or 0
    next_version_number = max_version_number + 1

    metadata = {
        "publisher": publisher,
        "name": name,
        "version": target_version,
        "sha256": sha256,
    }
    if resolved_display_name:
        metadata["display_name"] = resolved_display_name
    if resolved_engine_range:
        metadata["engine_range"] = resolved_engine_range

    file_buffer = io.BytesIO(file_bytes)
    storage_meta = await storage_service.upload_file(
        file_data=file_buffer,
        object_key=object_key,
        content_type=file.content_type,
        metadata=metadata,
    )

    new_version = ExtensionVersion(
        extension_id=extension.id,
        version=target_version,
        version_number=next_version_number,
        prerelease=prerelease,
        engine_range=resolved_engine_range,
        size=len(file_bytes),
        sha256=sha256,
        content_type=storage_meta.content_type
        if storage_meta.content_type
        else (file.content_type or "application/octet-stream"),
        object_key=object_key,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    if created:
        db.refresh(extension)

    return ExtensionPublishResponse(
        publisher=extension.publisher,
        name=extension.name,
        version=new_version.version,
        version_number=new_version.version_number,
        engine_range=new_version.engine_range,
        yanked=new_version.yanked,
        size=new_version.size,
        sha256=new_version.sha256,
        content_type=new_version.content_type,
        created_at=new_version.created_at,
        published_at=new_version.published_at,
        object_key=new_version.object_key,
    )


@extensions_router.get(
    "/{extension_identity}/download",
    status_code=302,
)
async def download_extension(
    extension_identity: str,
    version: Optional[str] = Query(None, description="Version specifier or 'latest'"),
    permissions: Principal = Depends(get_current_permissions),
    db: Session = Depends(get_db),
    storage_service=Depends(get_storage_service),
):
    # if not permissions.permitted("extension", "get"):
    #     raise ForbiddenException("You don't have permission to download extensions")

    publisher, name = _split_identity(extension_identity)
    extension = _get_extension_or_404(db, publisher, name)

    specifier = _coerce_specifier(version or "latest")

    versions_query = db.query(ExtensionVersion).filter(
        ExtensionVersion.extension_id == extension.id,
        ExtensionVersion.yanked.is_(False),
    )
    versions = versions_query.all()
    matched = _select_version(versions, specifier)
    if not matched:
        raise NotFoundException("No matching extension version found")

    presigned = await storage_service.generate_presigned_url(
        object_key=matched.object_key,
        method="GET",
    )

    return RedirectResponse(url=presigned.url, status_code=302)


@extensions_router.get(
    "/{extension_identity}/versions",
    response_model=ExtensionVersionListResponse,
)
async def list_extension_versions(
    extension_identity: str,
    include_yanked: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    permissions: Principal = Depends(get_current_permissions),
    db: Session = Depends(get_db),
):
    # if not permissions.permitted("extension", "list"):
    #     raise ForbiddenException("You don't have permission to list extension versions")

    publisher, name = _split_identity(extension_identity)
    extension = _get_extension_or_404(db, publisher, name)

    query = db.query(ExtensionVersion).filter(
        ExtensionVersion.extension_id == extension.id,
    )
    if not include_yanked:
        query = query.filter(ExtensionVersion.yanked.is_(False))

    if cursor:
        cursor_version_num = _decode_cursor(cursor)
        query = query.filter(ExtensionVersion.version_number < cursor_version_num)

    query = query.order_by(ExtensionVersion.version_number.desc())

    rows = query.limit(limit + 1).all()
    items = [ExtensionVersionListItem.model_validate(row) for row in rows[:limit]]

    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = _encode_cursor(last.version_number)

    return ExtensionVersionListResponse(items=items, next_cursor=next_cursor)


@extensions_router.get("/", response_model=List[str])
async def list_extensions(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    permissions: Principal = Depends(get_current_permissions),
    db: Session = Depends(get_db),
):
    # if not permissions.permitted("extension", "list"):
    #     raise ForbiddenException("You don't have permission to list extensions")

    rows = (
        db.query(Extension.publisher, Extension.name)
        .order_by(Extension.publisher.asc(), Extension.name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [f"{publisher}.{name}" for publisher, name in rows]


@extensions_router.get(
    "/{extension_identity}",
    response_model=ExtensionMetadata,
)
async def get_extension_metadata(
    extension_identity: str,
    permissions: Principal = Depends(get_current_permissions),
    db: Session = Depends(get_db),
):
    # if not permissions.permitted("extension", "get"):
    #     raise ForbiddenException("You don't have permission to view extensions")

    publisher, name = _split_identity(extension_identity)
    extension = _get_extension_or_404(db, publisher, name)

    version_count = (
        db.query(func.count(ExtensionVersion.id))
        .filter(ExtensionVersion.extension_id == extension.id)
        .scalar()
    ) or 0

    latest_version = (
        db.query(ExtensionVersion)
        .filter(
            ExtensionVersion.extension_id == extension.id,
            ExtensionVersion.yanked.is_(False),
        )
        .order_by(
            ExtensionVersion.published_at.desc(),
            ExtensionVersion.id.desc(),
        )
        .first()
    )

    latest_payload = (
        ExtensionVersionListItem.model_validate(latest_version)
        if latest_version
        else None
    )

    return ExtensionMetadata(
        id=extension.id,
        created_at=extension.created_at,
        updated_at=extension.updated_at,
        publisher=extension.publisher,
        name=extension.name,
        display_name=extension.display_name,
        description=extension.description,
        version_count=version_count,
        latest_version=latest_payload,
    )


@extensions_router.patch(
    "/{extension_identity}/versions/{version}",
    response_model=ExtensionVersionDetail,
)
async def update_extension_version(
    extension_identity: str,
    version: str,
    payload: ExtensionVersionYankRequest,
    permissions: Principal = Depends(get_current_permissions),
    db: Session = Depends(get_db),
):
    if not permissions.permitted("extension", "update"):
        raise ForbiddenException("You don't have permission to modify extension versions")

    publisher, name = _split_identity(extension_identity)
    extension = _get_extension_or_404(db, publisher, name)

    target_version = (
        db.query(ExtensionVersion)
        .filter(
            ExtensionVersion.extension_id == extension.id,
            ExtensionVersion.version == version,
        )
        .first()
    )
    if not target_version:
        raise NotFoundException("Extension version not found")

    target_version.yanked = payload.yanked
    db.commit()
    db.refresh(target_version)

    return ExtensionVersionDetail.model_validate(target_version)
