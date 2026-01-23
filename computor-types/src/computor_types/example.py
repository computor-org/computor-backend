"""
Pydantic interfaces for Example Library models.
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Union



from computor_types.custom_types import Ltree

from .base import BaseEntityGet, BaseEntityList, EntityInterface, ListQuery

class ExampleRepositoryCreate(BaseModel):
    """Create a new example repository."""
    name: str = Field(..., description="Human-readable name of the repository")
    description: Optional[str] = Field(None, description="Description of the repository")
    source_type: str = Field("git", description="Type of source: git, minio, github, s3, gitlab")
    source_url: str = Field(..., description="Repository URL (Git URL, MinIO path, etc.)")
    access_credentials: Optional[str] = Field(None, description="Encrypted credentials")
    default_version: Optional[str] = Field(None, description="Default version to sync from")
    organization_id: Optional[str] = None

class ExampleRepositoryGet(BaseEntityGet, ExampleRepositoryCreate):
    """Get example repository details."""
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ExampleRepositoryList(BaseModel):
    """List view of example repositories."""
    id: str
    name: str
    description: Optional[str] = None
    source_type: str
    source_url: str
    organization_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ExampleRepositoryUpdate(BaseModel):
    """Update example repository."""
    name: Optional[str] = None
    description: Optional[str] = None
    access_credentials: Optional[str] = None
    default_version: Optional[str] = None

class ExampleCreate(BaseModel):
    """Create a new example."""
    example_repository_id: str
    directory: str = Field(..., pattern="^[a-zA-Z0-9._-]+$")
    identifier: str = Field(..., description="Hierarchical identifier with dots as separators")
    title: str
    description: Optional[str] = None
    subject: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class ExampleGet(BaseEntityGet, ExampleCreate):
    """Get example details."""
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    # Relationships
    repository: Optional[ExampleRepositoryGet] = None
    versions: Optional[List['ExampleVersionGet']] = None
    dependencies: Optional[List['ExampleDependencyGet']] = None

    @field_validator('identifier', mode='before')
    @classmethod
    def cast_ltree_to_str(cls, value):
        return str(value)

    model_config = ConfigDict(from_attributes=True)

class ExampleList(BaseEntityList):
    """List view of examples."""
    id: str
    directory: str
    identifier: str
    title: str
    subject: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    example_repository_id: str

    @field_validator('identifier', mode='before')
    @classmethod
    def cast_ltree_to_str(cls, value):
        return str(value)

    model_config = ConfigDict(from_attributes=True)

class ExampleUpdate(BaseModel):
    """Update example."""
    identifier: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

class ExampleVersionCreate(BaseModel):
    """Create a new example version."""
    example_id: str
    version_tag: str = Field(..., max_length=64)
    version_number: int = Field(..., ge=1)
    storage_path: str
    meta_yaml: str = Field(..., description="Content of meta.yaml")
    test_yaml: Optional[str] = Field(None, description="Content of test.yaml")

class ExampleVersionGet(BaseEntityGet):
    """Get example version details."""
    id: str
    example_id: str
    version_tag: str
    version_number: int
    storage_path: str
    meta_yaml: str
    test_yaml: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ExampleVersionList(BaseModel):
    """List view of example versions."""
    id: str
    version_tag: str
    version_number: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ExampleVersionQuery(ListQuery):
    """Query parameters for listing example versions (filtering)."""
    version_tag: Optional[str] = None

class ExampleDependencyCreate(BaseModel):
    """Create example dependency."""
    example_id: str
    depends_id: str
    version_constraint: Optional[str] = Field(None, description="Version constraint (e.g., '>=1.2.0', '^2.1.0'). NULL means latest version.")

class ExampleDependencyGet(BaseModel):
    """Get example dependency details."""
    id: str
    example_id: str
    depends_id: str
    version_constraint: Optional[str] = Field(None, description="Version constraint string")
    created_at: datetime

    # Relationship
    dependency: Optional[ExampleList] = None

    model_config = ConfigDict(from_attributes=True)

class ExampleQuery(ListQuery):
    """Query parameters for listing examples."""
    id: Optional[str] = Field(None, description="Filter by example ID")
    repository_id: Optional[str] = Field(None, description="Filter by repository ID")
    identifier: Optional[str] = Field(None, description="Filter by identifier (supports Ltree patterns with *)")
    title: Optional[str] = Field(None, description="Filter by title (partial match)")
    category: Optional[str] = Field(None, description="Filter by category")
    tags: Optional[List[str]] = Field(None, description="Filter by tags (array contains all)")
    search: Optional[str] = Field(None, description="Full-text search in title and description")

class ExampleRepositoryQuery(ListQuery):
    """Query parameters for listing repositories."""
    id: Optional[str] = Field(None, description="Filter by repository ID")
    name: Optional[str] = Field(None, description="Filter by name (partial match)")
    source_type: Optional[str] = Field(None, description="Filter by source type")
    organization_id: Optional[str] = Field(None, description="Filter by organization ID")

# Search functions


# EntityInterface classes
class ExampleRepositoryInterface(EntityInterface):
    """Interface for ExampleRepository entity."""
    create = ExampleRepositoryCreate
    get = ExampleRepositoryGet
    list = ExampleRepositoryList
    update = ExampleRepositoryUpdate
    query = ExampleRepositoryQuery

class ExampleInterface(EntityInterface):
    """Interface for Example entity."""
    create = ExampleCreate
    get = ExampleGet
    list = ExampleList
    update = ExampleUpdate
    query = ExampleQuery

class ExampleUploadRequest(BaseModel):
    """Request to upload an example to storage."""
    repository_id: str
    directory: str = Field(..., pattern="^[a-zA-Z0-9._-]+$")
    files: Dict[str, Union[str, bytes]] = Field(..., description="Map of filename to content. Text files as UTF-8 strings, binary files as either base64-encoded strings or raw bytes. Must include meta.yaml")

class ExampleBatchUploadRequest(BaseModel):
    """Request to upload multiple examples to storage."""
    repository_id: str
    examples: List[Dict[str, Any]] = Field(..., description="List of examples with directory and files")

class ExampleFileSet(BaseModel):
    """Files for a single example."""
    example_id: str
    version_id: str
    version_tag: str
    directory: str
    identifier: str
    title: str
    files: Dict[str, str] = Field(..., description="Map of filename to content")
    meta_yaml: str
    test_yaml: Optional[str] = None

class ExampleDownloadResponse(BaseModel):
    """Response containing downloaded example files."""
    example_id: str
    version_id: Optional[str] = None
    version_tag: str
    identifier: str = Field(..., description="Hierarchical identifier of the example (e.g., itpcp.pgph.py.quadratic_eq)")
    directory: str = Field(..., description="Directory name of the example")
    files: Dict[str, str] = Field(..., description="Map of filename to content")
    meta_yaml: str
    test_yaml: Optional[str] = None
    # Dependencies included when with_dependencies=True
    dependencies: Optional[List[ExampleFileSet]] = Field(None, description="Dependency examples when with_dependencies=True")

# Fix forward references
ExampleGet.model_rebuild()
