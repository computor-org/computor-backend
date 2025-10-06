"""
FastAPI endpoints for Example Library management.
"""

import base64
import zipfile
import mimetypes
import io
import json
import logging
import re
import yaml
from typing import List, Optional, Tuple
# UUID type removed - using str for all IDs
from datetime import datetime, timezone
from ..custom_types import Ltree
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from ..database import get_db
from computor_backend.permissions.principal import Principal
from computor_types.example import (
    ExampleGet,
    ExampleList,
    ExampleVersionCreate,
    ExampleVersionGet,
    ExampleVersionList,
    ExampleDependencyCreate,
    ExampleDependencyGet,
    ExampleUploadRequest,
    ExampleDownloadResponse,
    ExampleFileSet,
    ExampleInterface,
    ExampleQuery,
)
from ..model.example import ExampleRepository, Example, ExampleVersion, ExampleDependency
from ..permissions.auth import get_current_principal
from computor_backend.business_logic.crud import (
    get_entity_by_id as get_id_db,
    list_entities as list_db
)
from ..api.exceptions import (
    NotFoundException,
    ForbiddenException,
    BadRequestException,
    NotImplementedException,
)
from ..redis_cache import get_redis_client, get_cache
from ..services.storage_service import get_storage_service
from ..services.version_resolver import VersionResolver
from ..services.dependency_sync import DependencySyncService
from ..repositories import ExampleVersionRepository, ExampleDependencyRepository

logger = logging.getLogger(__name__)

examples_router = APIRouter(prefix="/examples", tags=["examples"])

# Cache TTL values
CACHE_TTL_LIST = 300  # 5 minutes
CACHE_TTL_GET = 600   # 10 minutes

# Note: Basic CRUD operations are handled by CrudRouter in server.py

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _guess_content_type(filename: str, is_binary: bool) -> str:
    """Return a reasonable content-type for a given filename.

    Preference order:
    1) Known multi-part extensions (e.g. .tar.gz/.tgz)
    2) Explicit overrides for common types
    3) Python's mimetypes.guess_type
    4) Fallback to application/octet-stream for binary, text/plain for text
    """
    name = filename.lower()

    # Multi-part extensions first
    if name.endswith('.tar.gz') or name.endswith('.tgz'):
        return 'application/x-tar'

    # Explicit overrides to keep behavior consistent across platforms
    overrides = {
        '.yaml': 'text/yaml',
        '.yml': 'text/yaml',
        '.json': 'application/json',
        '.xml': 'application/xml',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.py': 'text/x-python',
        '.java': 'text/x-java',
        '.c': 'text/x-c',
        '.h': 'text/x-c',
        '.cpp': 'text/x-c++',
        '.hpp': 'text/x-c++',
        '.cc': 'text/x-c++',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.pdf': 'application/pdf',
        '.zip': 'application/zip',
        '.tar': 'application/x-tar',
        '.md': 'text/markdown',
        '.txt': 'text/plain',
    }

    for ext, ctype in overrides.items():
        if name.endswith(ext):
            return ctype

    # Fall back to mimetypes
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed

    # Final fallback based on binary/text
    return 'application/octet-stream' if is_binary else 'text/plain'


_BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.tar', '.tgz', '.tar.gz',
}


def _is_binary_by_extension(filename: str) -> bool:
    name = filename.lower()
    return any(name.endswith(ext) for ext in _BINARY_EXTENSIONS)


def _extract_file_bytes(filename: str, content: object) -> Tuple[io.BytesIO, bool]:
    """Convert provided content to bytes and determine binary/text.

    - bytes -> passthrough (binary)
    - str with data URI -> base64 decode (binary)
    - str and binary-suspect extension -> try base64 decode; else encode as UTF-8 (text)
    - str generic -> attempt safe base64 decode (validate), else encode UTF-8 (text)
    """
    # Raw bytes
    if isinstance(content, (bytes, bytearray)):
        return io.BytesIO(bytes(content)), True

    if not isinstance(content, str):
        # Unknown type: coerce to string and store as text
        data = io.BytesIO(str(content).encode('utf-8'))
        return data, False

    # Strings
    text = content

    # Handle data URI
    if text.startswith('data:'):
        try:
            base64_marker = ';base64,'
            idx = text.find(base64_marker)
            if idx != -1:
                b64 = text[idx + len(base64_marker):]
                return io.BytesIO(base64.b64decode(b64, validate=False)), True
        except Exception:
            pass  # fall back to other handling

    # Normalize whitespace
    clean = text.replace('\n', '').replace('\r', '').replace(' ', '').replace('\t', '')

    # If extension suggests binary, aggressively try base64 decode first
    if _is_binary_by_extension(filename):
        try:
            return io.BytesIO(base64.b64decode(clean, validate=True)), True
        except Exception:
            # Fall back to raw text bytes; still store something
            return io.BytesIO(text.encode('utf-8')), False

    # For non-binary extensions, attempt a safe base64 decode only if characters match
    base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
    if len(clean) % 4 == 0 and base64_pattern.match(clean):
        try:
            decoded = base64.b64decode(clean, validate=True)
            return io.BytesIO(decoded), True
        except Exception:
            pass

    # Default: treat as UTF-8 text
    return io.BytesIO(text.encode('utf-8')), False


_TEXT_CONTENT_TYPES = {
    'application/json',
    'application/xml',
    'application/javascript',
    'application/x-javascript',
    'text/plain',
    'text/html',
    'text/css',
    'text/csv',
    'text/markdown',
    'text/yaml',
    'text/x-python',
    'text/x-java',
    'text/x-c',
    'text/x-c++',
    'image/svg+xml',
}


def _is_text_content_type(content_type: Optional[str]) -> bool:
    if not content_type:
        return False
    if content_type.startswith('text/'):
        return True
    return content_type in _TEXT_CONTENT_TYPES


def _encode_for_response(filename: str, data: bytes, content_type: Optional[str]) -> str:
    """Return a string payload suitable for ExampleDownloadResponse.files.

    - Text types: UTF-8 decoded string
    - Binary types: Data URI with base64
    """
    if _is_text_content_type(content_type):
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            # Fall back to base64 data URI if decoding fails
            b64 = base64.b64encode(data).decode('ascii')
            ctype = content_type or _guess_content_type(filename, True)
            return f"data:{ctype};base64,{b64}"

    # If content-type unknown, attempt to decode as UTF-8 text
    if not content_type:
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            pass

    # Binary: base64 data URI
    b64 = base64.b64encode(data).decode('ascii')
    ctype = content_type or _guess_content_type(filename, True)
    return f"data:{ctype};base64,{b64}"

# ==============================================================================
# Example Endpoints
# ==============================================================================

@examples_router.get("", response_model=List[ExampleList])
async def list_examples(
    response: Response,
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
    params: ExampleQuery = Depends(),
    redis_client=Depends(get_redis_client),
):
    """List all examples."""
    list_result, total = await list_db(permissions, db, params, ExampleInterface)
    response.headers["X-Total-Count"] = str(total)
    
    # Cache the result
    # cache_data = {
    #     "items": [item.model_dump(mode='json') for item in list_result],
    #     "total": total
    # }
    # await cache.set(cache_key, cache_data, ttl=self.dto.cache_ttl)
    
    return list_result


@examples_router.get("/{example_id}", response_model=ExampleGet)
async def get_example(
    example_id: str,
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
    redis_client=Depends(get_redis_client),
):
    """Get a specific example."""
    return await get_id_db(permissions, db, example_id, ExampleInterface)


# ==============================================================================
# Example Version Endpoints
# ==============================================================================

@examples_router.post("/{example_id}/versions", response_model=ExampleVersionGet)
async def create_version(
    example_id: str,
    version: ExampleVersionCreate,
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
):
    """Create a new version for an example."""
    # Check permissions
    if not permissions.permitted("example", "create"):
        raise ForbiddenException("You don't have permission to create versions")

    # Initialize repository
    version_repo = ExampleVersionRepository(db, get_cache())

    # Verify example exists
    example = db.query(Example).filter(Example.id == example_id).first()
    if not example:
        raise NotFoundException(f"Example {example_id} not found")

    # Ensure example_id matches
    if version.example_id != example_id:
        raise BadRequestException("Example ID mismatch")

    # Create version
    db_version = ExampleVersion(
        **version.model_dump(),
        created_by=permissions.user_id,
    )

    # Create via repository (cache invalidation automatic)
    db_version = version_repo.create(db_version)

    return db_version


from computor_types.example import ExampleVersionQuery


@examples_router.get("/{example_id}/versions", response_model=List[ExampleVersionList])
async def list_versions(
    example_id: str,
    params: ExampleVersionQuery = Depends(),
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
    redis_client=Depends(get_redis_client),
):
    """List all versions of an example."""
    # Check permissions
    if not permissions.permitted("example", "list"):
        raise ForbiddenException("You don't have permission to view versions")

    # Initialize repository
    version_repo = ExampleVersionRepository(db, get_cache())

    # Get versions via repository
    if params and params.version_tag:
        # Filter by version_tag
        version = version_repo.find_by_version_tag(example_id, params.version_tag)
        versions = [version] if version else []
    else:
        # Get all versions for example
        versions = version_repo.find_by_example(example_id)

    # Convert to response model
    result = [ExampleVersionList.model_validate(v) for v in versions]

    return result


@examples_router.get("/versions/{version_id}", response_model=ExampleVersionGet)
async def get_version(
    version_id: str,
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
    redis_client=Depends(get_redis_client),
):
    """Get a specific version."""
    # Check permissions
    if not permissions.permitted("example", "get"):
        raise ForbiddenException("You don't have permission to view versions")

    # Initialize repository
    version_repo = ExampleVersionRepository(db, get_cache())

    # Get version via repository (caching automatic)
    version = version_repo.get_by_id(version_id)

    if not version:
        raise NotFoundException(f"Version {version_id} not found")

    # Convert to response model
    return ExampleVersionGet.model_validate(version)


# ==============================================================================
# Example Dependencies Endpoints
# ==============================================================================

@examples_router.post("/{example_id}/dependencies", response_model=ExampleDependencyGet)
async def add_dependency(
    example_id: str,
    dependency: ExampleDependencyCreate,
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
):
    """Add a dependency to an example."""
    # Check permissions
    if not permissions.permitted("example", "update"):
        raise ForbiddenException("You don't have permission to modify dependencies")

    # Initialize repository
    dependency_repo = ExampleDependencyRepository(db, get_cache())

    # Verify example exists
    example = db.query(Example).filter(Example.id == example_id).first()
    if not example:
        raise NotFoundException(f"Example {example_id} not found")

    # Verify dependency exists
    depends_on = db.query(Example).filter(Example.id == dependency.depends_id).first()
    if not depends_on:
        raise NotFoundException(f"Dependency example {dependency.depends_id} not found")

    # Ensure example_id matches
    if dependency.example_id != example_id:
        raise BadRequestException("Example ID mismatch")

    # Check for circular dependencies
    if dependency.depends_id == example_id:
        raise BadRequestException("An example cannot depend on itself")

    # Check for circular dependencies (advanced)
    if dependency_repo.has_circular_dependency(example_id, dependency.depends_id):
        raise BadRequestException("Adding this dependency would create a circular dependency")

    # Create dependency via repository (cache invalidation automatic)
    db_dependency = ExampleDependency(**dependency.model_dump())
    db_dependency = dependency_repo.create(db_dependency)

    return db_dependency


@examples_router.get("/{example_id}/dependencies", response_model=List[ExampleDependencyGet])
async def list_dependencies(
    example_id: str,
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
):
    """List all dependencies of an example."""
    # Check permissions
    if not permissions.permitted("example", "list"):
        raise ForbiddenException("You don't have permission to view dependencies")

    # Initialize repository
    dependency_repo = ExampleDependencyRepository(db, get_cache())

    # Get dependencies via repository
    dependencies = dependency_repo.find_dependencies_of(example_id)

    return [ExampleDependencyGet.model_validate(d) for d in dependencies]


@examples_router.delete("/dependencies/{dependency_id}")
async def remove_dependency(
    dependency_id: str,
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
):
    """Remove a dependency."""
    # Check permissions
    if not permissions.permitted("example", "update"):
        raise ForbiddenException("You don't have permission to modify dependencies")

    # Initialize repository
    dependency_repo = ExampleDependencyRepository(db, get_cache())

    # Get dependency
    dependency = dependency_repo.get_by_id(dependency_id)

    if not dependency:
        raise NotFoundException(f"Dependency {dependency_id} not found")

    # Delete dependency via repository (cache invalidation automatic)
    dependency_repo.delete(dependency)

    return {"message": "Dependency removed successfully"}


# ==============================================================================
# Upload/Download Endpoints
# ==============================================================================

@examples_router.post("/upload", response_model=ExampleVersionGet)
async def upload_example(
    request: ExampleUploadRequest,
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
    storage_service=Depends(get_storage_service),
):
    """Upload an example to storage (MinIO)."""
    # Check permissions
    if not permissions.permitted("example", "upload"):
        raise ForbiddenException("You don't have permission to upload examples")
    
    # Verify repository exists and is MinIO type
    repository = db.query(ExampleRepository).filter(
        ExampleRepository.id == request.repository_id
    ).first()
    
    if not repository:
        raise NotFoundException(f"Repository {request.repository_id} not found")
    
    if repository.source_type == "git":
        raise NotImplementedException("Git upload not implemented - use git push instead")
    
    if repository.source_type not in ["minio", "s3"]:
        raise BadRequestException(f"Upload not supported for {repository.source_type} repositories")
    
    # Support two input modes:
    # 1) Classic: request.files contains all files including 'meta.yaml'
    # 2) Zipped:  request.files contains a single .zip which we extract here

    # Detect zipped upload (first .zip file wins)
    extracted_files = None
    zip_entry_name = next((name for name in request.files.keys() if name.lower().endswith('.zip')), None)
    if zip_entry_name is not None:
        try:
            zip_bytes_io, _ = _extract_file_bytes(zip_entry_name, request.files[zip_entry_name])
            with zipfile.ZipFile(zip_bytes_io, 'r') as zf:
                files: dict[str, bytes] = {}
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    # Normalize arcname and skip any unsafe paths
                    raw_name = info.filename
                    # Exclude MacOS and hidden dot entries
                    if raw_name.startswith('__MACOSX/') or '/.' in raw_name or raw_name.endswith('.meta.yaml'):
                        continue
                    # Normalize to avoid zip slip
                    norm_name = raw_name.replace('\\', '/')
                    norm_name = norm_name.lstrip('/')
                    # Collapse .. segments
                    parts = []
                    for part in norm_name.split('/'):
                        if part in ('', '.'):
                            continue
                        if part == '..':
                            # Unsafe path
                            parts = []
                            break
                        parts.append(part)
                    if not parts:
                        continue
                    safe_name = '/'.join(parts)
                    # Read raw bytes; text/binary handled later
                    with zf.open(info, 'r') as fp:
                        data = fp.read()
                        files[safe_name] = data
                extracted_files = files
        except Exception as e:
            logger.exception("Failed to extract uploaded zip for example")
            raise BadRequestException(f"Invalid zip upload: {e}")

    # Choose file source
    incoming_files = extracted_files if extracted_files is not None else request.files

    # Validate that meta.yaml is included
    if 'meta.yaml' not in incoming_files:
        raise BadRequestException("meta.yaml file is required")
    
    # Parse meta.yaml to extract example metadata
    try:
        meta_content = incoming_files['meta.yaml']
        if isinstance(meta_content, (bytes, bytearray)):
            meta_str = meta_content.decode('utf-8', errors='replace')
        else:
            meta_str = str(meta_content)
        meta_data = yaml.safe_load(meta_str)
    except yaml.YAMLError as e:
        raise BadRequestException(f"Invalid meta.yaml format: {str(e)}")
    
    # Extract metadata from meta.yaml
    title = meta_data.get('title', request.directory.replace('-', ' ').replace('_', ' ').title())
    description = meta_data.get('description', '')
    slug = meta_data.get('slug', request.directory.replace('-', '.').replace('_', '.'))
    
    # Extract version from meta.yaml (use exactly as specified)
    version_tag = meta_data.get('version', '1.0')
    
    # Extract tags and other metadata
    tags = []
    if 'tags' in meta_data:
        tags = meta_data['tags'] if isinstance(meta_data['tags'], list) else [meta_data['tags']]
    
    # Check if example exists
    example = db.query(Example).filter(
        Example.example_repository_id == request.repository_id,
        Example.directory == request.directory
    ).first()
    
    # Create or update example
    if not example:
        example = Example(
            example_repository_id=request.repository_id,
            directory=request.directory,
            identifier=Ltree(slug),
            title=title,
            description=description,
            tags=tags,
            created_by=permissions.user_id,
            updated_by=permissions.user_id,
        )
        db.add(example)
        db.flush()
    else:
        # Update existing example with new metadata
        example.identifier = Ltree(slug)
        example.title = title
        example.description = description
        example.tags = tags
        example.updated_by = permissions.user_id
    
    # Initialize repository
    version_repo = ExampleVersionRepository(db, get_cache())

    # Check if this version already exists
    existing_version = version_repo.find_by_version_tag(example.id, version_tag)
    
    # Check if meta.yaml indicates this should update an existing version
    should_update = meta_data.get('update_existing', False) or meta_data.get('overwrite', False)
    
    if existing_version and not should_update:
        raise BadRequestException(
            f"Version '{version_tag}' already exists for this example. "
            f"To update it, add 'update_existing: true' to meta.yaml or use a different version tag."
        )
    
    # Determine version number and storage path
    if existing_version:
        # Updating existing version
        version_number = existing_version.version_number
        storage_path = existing_version.storage_path
    else:
        # Creating new version - use repository method
        version_number = version_repo.get_next_version_number(example.id)
        storage_path = f"examples/{repository.id}/{example.directory}/v{version_number}"
    
    # Upload files to MinIO
    bucket_name = repository.source_url.split('/')[0]  # First part is bucket
    
    # Get test.yaml content if it exists
    test_yaml_content = incoming_files.get('test.yaml')
    if isinstance(test_yaml_content, (bytes, bytearray)):
        test_yaml_content = test_yaml_content.decode('utf-8', errors='replace')

    for filename, content in incoming_files.items():
        if filename.lower().endswith('.zip'):
            # Do not store the container zip itself
            continue
        object_key = f"{storage_path}/{filename}"
        
        # Convert incoming content to bytes and determine if it's binary
        file_data, is_binary = _extract_file_bytes(filename, content)
        if file_data is None:
            logger.error(f"Could not process content for {filename}")
            continue
        
        # Determine content type based on filename and whether it is binary
        content_type = _guess_content_type(filename, is_binary)
        
        # Upload file
        await storage_service.upload_file(
            file_data=file_data,
            object_key=object_key,
            bucket_name=bucket_name,
            content_type=content_type,
        )
    
    # Create or update version record
    if existing_version:
        # Update existing version
        existing_version.meta_yaml = meta_str
        existing_version.test_yaml = test_yaml_content
        existing_version.updated_at = func.now()
        version = version_repo.update(existing_version)
    else:
        # Create new version
        version = ExampleVersion(
            example_id=example.id,
            version_tag=version_tag,
            version_number=version_number,
            storage_path=storage_path,
            meta_yaml=meta_str,
            test_yaml=test_yaml_content,
            created_by=permissions.user_id,
        )
        version = version_repo.create(version)
    
    # Process testDependencies from meta.yaml (check both root and properties)
    test_dependencies = meta_data.get('testDependencies', [])
    if not test_dependencies and 'properties' in meta_data:
        test_dependencies = meta_data['properties'].get('testDependencies', [])
    
    logger.info(f"Meta data keys: {list(meta_data.keys())}")
    if 'properties' in meta_data:
        logger.info(f"Properties keys: {list(meta_data['properties'].keys())}")
    logger.info(f"testDependencies found: {test_dependencies}")
    
    # Sync dependencies from meta.yaml to database
    dependency_sync = DependencySyncService(db)
    dependency_sync.sync_dependencies_from_meta(
        example=example,
        test_dependencies=test_dependencies,
        repository_id=repository.id
    )

    # Cache invalidation is automatic via repository

    return version


@examples_router.get("/{example_id}/download", response_model=ExampleDownloadResponse)
async def download_example_latest(
    example_id: str,
    with_dependencies: bool = Query(False, description="Include all dependencies recursively"),
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
    storage_service=Depends(get_storage_service),
):
    """Download the latest version of an example from storage, optionally with all dependencies."""
    # Check permissions
    if not permissions.permitted("example", "download"):
        raise ForbiddenException("You don't have permission to download examples")
    
    # Get example with repository relationship
    example = db.query(Example).filter(Example.id == example_id).first()
    if not example:
        raise NotFoundException(f"Example {example_id} not found")
    
    # Initialize repository
    version_repo = ExampleVersionRepository(db, get_cache())

    # Get the latest version
    latest_version = version_repo.find_latest_version(example_id)
    
    if not latest_version:
        # If no version exists, return minimal response with just the example directory structure
        # Load repository relationship
        repository = db.query(ExampleRepository).filter(
            ExampleRepository.id == example.example_repository_id
        ).first()
        
        if not repository:
            raise NotFoundException(f"Repository for example {example_id} not found")
        
        # For Git repositories, we can't download directly
        if repository.source_type == "git":
            # Return basic structure for Git-based examples
            return ExampleDownloadResponse(
                example_id=example.id,
                version_id=None,
                version_tag="latest",
                files={
                    "README.md": f"# {example.title}\n\n{example.description or 'No description available'}\n\nThis example is stored in a Git repository.\nClone the repository to access the files.",
                    "meta.yaml": f"slug: {example.identifier}\ntitle: {example.title}\ndescription: {example.description or ''}\n"
                },
                meta_yaml=f"slug: {example.identifier}\ntitle: {example.title}\n",
                test_yaml=None,
                dependencies=None,
            )
        
        raise NotFoundException(f"No versions found for example {example_id}")
    
    # Use the existing download logic with the version ID
    return await download_example_version(
        latest_version.id,
        with_dependencies,
        db,
        permissions,
        storage_service
    )


@examples_router.get("/download/{version_id}", response_model=ExampleDownloadResponse)
async def download_example_version(
    version_id: str,
    with_dependencies: bool = Query(False, description="Include all dependencies recursively"),
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
    storage_service=Depends(get_storage_service),
):
    """Download a specific example version from storage, optionally with all dependencies."""
    # Check permissions
    if not permissions.permitted("example", "download"):
        raise ForbiddenException("You don't have permission to download examples")
    
    # Initialize repository
    version_repo = ExampleVersionRepository(db, get_cache())

    # Get version
    version = version_repo.get_by_id(version_id)
    
    if not version:
        raise NotFoundException(f"Version {version_id} not found")
    
    # Get example and repository
    example = version.example
    repository = example.repository
    
    # Initialize dependency repository
    dependency_repo = ExampleDependencyRepository(db, get_cache())

    # Helper function to get all dependencies with version constraints recursively
    def get_all_dependencies_with_constraints(example_id: str, visited: set = None) -> List[tuple]:
        if visited is None:
            visited = set()

        if example_id in visited:
            return []  # Avoid circular dependencies

        visited.add(example_id)
        all_deps = []

        # Get direct dependencies with version constraints via repository
        dependencies = dependency_repo.find_dependencies_of(example_id)
        
        for dep in dependencies:
            if dep.depends_id not in visited:
                all_deps.append((dep.depends_id, dep.version_constraint))
                # Recursively get dependencies of dependencies
                sub_deps = get_all_dependencies_with_constraints(dep.depends_id, visited.copy())
                all_deps.extend(sub_deps)
        
        # Remove duplicates while preserving version constraints
        # If same dependency appears with different constraints, keep the first one
        seen = set()
        unique_deps = []
        for dep_id, constraint in all_deps:
            if dep_id not in seen:
                unique_deps.append((dep_id, constraint))
                seen.add(dep_id)
        
        return unique_deps
    
    # Helper function to download files for an example version
    async def download_example_files(ex_version: ExampleVersion):
        ex_example = ex_version.example
        ex_repository = ex_example.repository
        
        if ex_repository.source_type == "git":
            raise NotImplementedException("Git download not implemented - use git clone instead")
        
        if ex_repository.source_type not in ["minio", "s3"]:
            raise BadRequestException(f"Download not supported for {ex_repository.source_type} repositories")
        
        # Get files from MinIO
        bucket_name = ex_repository.source_url.split('/')[0]
        
        # List all objects in the version path
        objects = await storage_service.list_objects(
            bucket_name=bucket_name,
            prefix=ex_version.storage_path,
        )
        
        files = {}
        for obj in objects:
            if obj.object_name.endswith('/'):
                continue  # Skip directories
            
            # Get relative filename
            filename = obj.object_name.replace(f"{ex_version.storage_path}/", "")
            
            # Download file content and fetch content-type
            file_data = await storage_service.download_file(
                bucket_name=bucket_name,
                object_key=obj.object_name,
            )
            info = await storage_service.get_object_info(
                bucket_name=bucket_name,
                object_key=obj.object_name,
            )
            
            # Encode based on content-type
            files[filename] = _encode_for_response(filename, file_data, info.content_type)
        
        return files
    
    # Download main example files
    main_files = await download_example_files(version)
    
    # Handle dependencies if requested
    dependency_files = []
    if with_dependencies:
        dependencies = get_all_dependencies_with_constraints(example.id)
        version_resolver = VersionResolver(db)
        
        for dep_example_id, version_constraint in dependencies:
            dep_example = db.query(Example).filter(Example.id == dep_example_id).first()
            if not dep_example:
                continue
                
            # Resolve version constraint to specific version
            dep_version = version_resolver.resolve_constraint(
                str(dep_example.identifier), 
                version_constraint
            )
            
            if not dep_version:
                continue
            
            # Download dependency files
            dep_files = await download_example_files(dep_version)
            
            dependency_files.append({
                "example_id": str(dep_example.id),
                "version_id": str(dep_version.id),
                "version_tag": dep_version.version_tag,
                "directory": dep_example.directory,
                "identifier": str(dep_example.identifier),
                "title": dep_example.title,
                "files": dep_files,
                "meta_yaml": dep_version.meta_yaml,
                "test_yaml": dep_version.test_yaml,
            })
    
    return ExampleDownloadResponse(
        example_id=example.id,
        version_id=version.id,
        version_tag=version.version_tag,
        files=main_files,
        meta_yaml=version.meta_yaml,
        test_yaml=version.test_yaml,
        dependencies=dependency_files if with_dependencies else None,
    )


@examples_router.get("/{example_id}/dependencies", response_model=List[ExampleDependencyGet])
async def get_example_dependencies(
    example_id: str,
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
):
    """Get all dependencies for an example with version constraints."""
    # Check permissions
    if not permissions.permitted("example", "list"):
        raise ForbiddenException("You don't have permission to read example dependencies")

    # Check if example exists
    example = db.query(Example).filter(Example.id == example_id).first()
    if not example:
        raise NotFoundException(f"Example {example_id} not found")

    # Initialize repository
    dependency_repo = ExampleDependencyRepository(db, get_cache())

    # Get dependencies via repository
    dependencies = dependency_repo.find_dependencies_of(example_id)

    return dependencies


@examples_router.post("/{example_id}/dependencies", response_model=ExampleDependencyGet)
async def create_example_dependency(
    example_id: str,
    dependency_data: ExampleDependencyCreate,
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
):
    """Create a new dependency relationship between examples."""
    # Check permissions
    if not permissions.permitted("example", "create"):
        raise ForbiddenException("You don't have permission to create example dependencies")

    # Initialize repository
    dependency_repo = ExampleDependencyRepository(db, get_cache())

    # Validate example exists
    example = db.query(Example).filter(Example.id == example_id).first()
    if not example:
        raise NotFoundException(f"Example {example_id} not found")

    # Validate dependency example exists
    dependency_example = db.query(Example).filter(Example.id == dependency_data.depends_id).first()
    if not dependency_example:
        raise NotFoundException(f"Dependency example {dependency_data.depends_id} not found")

    # Check if dependency already exists
    existing = dependency_repo.find_dependency_between(example_id, dependency_data.depends_id)

    if existing:
        raise BadRequestException(f"Dependency already exists between {example_id} and {dependency_data.depends_id}")

    # Check for circular dependencies
    if dependency_repo.has_circular_dependency(example_id, dependency_data.depends_id):
        raise BadRequestException("Adding this dependency would create a circular dependency")

    # Create dependency via repository (cache invalidation automatic)
    dependency = ExampleDependency(
        example_id=example_id,
        depends_id=dependency_data.depends_id,
        version_constraint=dependency_data.version_constraint
    )

    dependency = dependency_repo.create(dependency)

    return dependency


@examples_router.delete("/{example_id}/dependencies/{dependency_id}")
async def delete_example_dependency(
    example_id: str,
    dependency_id: str,
    db: Session = Depends(get_db),
    permissions: Principal = Depends(get_current_principal),
):
    """Delete a dependency relationship between examples."""
    # Check permissions
    if not permissions.permitted("example", "delete"):
        raise ForbiddenException("You don't have permission to delete example dependencies")

    # Initialize repository
    dependency_repo = ExampleDependencyRepository(db, get_cache())

    # Find dependency
    dependency = dependency_repo.get_by_id(dependency_id)

    if not dependency or dependency.example_id != example_id:
        raise NotFoundException(f"Dependency {dependency_id} not found for example {example_id}")

    # Delete dependency via repository (cache invalidation automatic)
    dependency_repo.delete(dependency)

    return {"message": "Dependency deleted successfully"}
