"""
SQLAlchemy model for Example.

This model represents individual examples/assignments within an ExampleRepository.
Each example is stored in its own directory with a flat structure.
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, ARRAY, ForeignKey, text, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import CheckConstraint, UniqueConstraint
try:
    from ..custom_types import LtreeType
except ImportError:
    # Fallback for Alembic context
    from computor_backend.custom_types import LtreeType

from .base import Base


class ExampleRepository(Base):
    """
    Repository containing examples/assignments in flat directory structure.
    
    Each repository contains multiple examples, each in its own directory.
    The repository can be public, private, or restricted to specific organizations.
    """
    
    __tablename__ = "example_repository"
    
    # Primary key
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    
    # Repository information
    name = Column(String(255), nullable=False, comment="Human-readable name of the repository")
    description = Column(Text, comment="Description of the repository and its contents")
    
    # Source repository information
    source_type = Column(
        String(20), 
        nullable=False, 
        default="git",
        comment="Type of repository source: git, minio, github, etc."
    )
    source_url = Column(Text, nullable=False, unique=True, comment="Repository URL (Git URL, MinIO path, etc.)")
    access_credentials = Column(Text, comment="Encrypted access credentials (Git token, MinIO credentials JSON, etc.)")
    default_version = Column(String(100), nullable=True, comment="Default version to sync from (branch for Git, optional for MinIO)")
    
    # Access control
    organization_id = Column(
        UUID, 
        ForeignKey("organization.id"),
        comment="Organization that owns this repository"
    )
    
    # Tracking
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID, ForeignKey("user.id"), comment="User who created this repository")
    updated_by = Column(UUID, ForeignKey("user.id"), comment="User who last updated this repository")
    
    # Relationships
    examples = relationship("Example", back_populates="repository", cascade="all, delete-orphan")
    organization = relationship("Organization", back_populates="example_repositories")
    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('git', 'minio', 'github', 's3', 'gitlab')",
            name="check_source_type"
        ),
    )
    
    def __repr__(self):
        return f"<ExampleRepository(id={self.id}, name='{self.name}')>"
    
    @property
    def needs_credentials(self) -> bool:
        """Check if repository requires access credentials."""
        return self.access_credentials is not None


class Example(Base):
    """
    Individual example/assignment within an ExampleRepository.
    
    Each example corresponds to a directory in the repository's flat structure.
    Contains educational metadata and file structure information.
    """
    
    __tablename__ = "example"
    
    # Primary key
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    
    # Repository relationship
    example_repository_id = Column(
        UUID, 
        ForeignKey("example_repository.id", ondelete="CASCADE"), 
        nullable=False,
        comment="Reference to the repository containing this example"
    )
    
    # Location within repository (flat structure)
    directory = Column(
        String(255), 
        nullable=False,
        comment="Name of the directory containing this example (e.g., 'hello-world')"
    )
    
    # Hierarchical identifier
    identifier = Column(
        LtreeType,
        nullable=False,
        comment="Hierarchical identifier using dots as separators"
    )
    
    # Example metadata
    title = Column(String(255), nullable=False, comment="Human-readable title of the example")
    description = Column(Text, comment="Detailed description of the example")
    
    # Organization and categorization
    category = Column(String(100), comment="Category for grouping examples")
    tags = Column(ARRAY(String), nullable=False, default=[], comment="Tags for searching and filtering")
    
    # Tracking
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID, ForeignKey("user.id"), comment="User who created this example record")
    updated_by = Column(UUID, ForeignKey("user.id"), comment="User who last updated this example record")
    
    # Relationships
    repository = relationship("ExampleRepository", back_populates="examples")
    created_by_user = relationship("User", foreign_keys=[created_by])
    updated_by_user = relationship("User", foreign_keys=[updated_by])
    
    # Course content relationships removed - CourseContent no longer has example_id
    # Access examples via CourseContentDeployment.example_version.example instead
    
    # Version relationships
    versions = relationship("ExampleVersion", back_populates="example", cascade="all, delete-orphan")
    
    # Dependency relationships
    dependencies = relationship("ExampleDependency", foreign_keys="ExampleDependency.example_id", back_populates="example")
    
    # Deployment tracking
    
    # Constraints
    __table_args__ = (
        # Unique constraint: one example per directory per repository
        UniqueConstraint("example_repository_id", "directory", name="unique_example_per_directory"),
        
        # Unique constraint: one example per identifier per repository
        UniqueConstraint("example_repository_id", "identifier", name="unique_example_per_identifier"),
        
        # Check constraints
        CheckConstraint(
            "directory ~ '^[a-zA-Z0-9._-]+$'",
            name="check_directory_format"
        ),
    )
    
    def __repr__(self):
        return f"<Example(id={self.id}, title='{self.title}', directory='{self.directory}')>"
    
    @property
    def full_path(self) -> str:
        """Get the full path within the repository."""
        return self.directory
    


class ExampleVersion(Base):
    """
    Version tracking for examples stored in MinIO or other versioned storage.
    
    Each version represents a snapshot of an example at a specific point in time.
    """
    
    __tablename__ = "example_version"
    
    # Primary key
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    
    # Example relationship
    example_id = Column(
        UUID, 
        ForeignKey("example.id", ondelete="CASCADE"), 
        nullable=False,
        comment="Reference to the example this version belongs to"
    )
    
    # Version information
    version_tag = Column(
        String(64), 
        nullable=False,
        comment="Version identifier (e.g., 'v1.0', 'v2.0-beta', commit hash)"
    )
    version_number = Column(
        Integer,
        nullable=False,
        comment="Sequential version number for ordering"
    )
    
    # Storage information
    storage_path = Column(
        Text,
        nullable=False,
        comment="Path in storage system (MinIO path, S3 key, etc.)"
    )
    
    # Content metadata: only promoted columns live in the DB. The full
    # meta.yaml / test.yaml documents are persisted to MinIO at
    # ``{storage_path}/meta.yaml`` and ``{storage_path}/test.yaml``;
    # download endpoints read them from there (with a Redis cache in
    # front) instead of duplicating the raw documents in Postgres.
    title = Column(
        String(255),
        nullable=True,
        comment="meta.yaml: title (per-version)",
    )
    description = Column(
        Text,
        nullable=True,
        comment="meta.yaml: description (per-version)",
    )
    language = Column(
        String(16),
        nullable=True,
        comment="meta.yaml: language",
    )
    license = Column(
        String(255),
        nullable=True,
        comment="meta.yaml: license",
    )
    execution_backend = Column(
        JSONB,
        nullable=True,
        comment="meta.yaml: properties.executionBackend full dict (slug + version + settings)",
    )
    student_submission_files = Column(
        ARRAY(Text),
        nullable=False,
        default=list,
        comment="meta.yaml: properties.studentSubmissionFiles",
    )
    additional_files = Column(
        ARRAY(Text),
        nullable=False,
        default=list,
        comment="meta.yaml: properties.additionalFiles",
    )
    student_templates = Column(
        ARRAY(Text),
        nullable=False,
        default=list,
        comment="meta.yaml: properties.studentTemplates",
    )
    test_files = Column(
        ARRAY(Text),
        nullable=False,
        default=list,
        comment="meta.yaml: properties.testFiles",
    )
    
    # Testing service: resolved at upload from
    # ``properties.executionBackend.slug`` in meta.yaml against the
    # ``service`` table. Stored as a real FK so assignment-time copies
    # are O(1) and the resolution can't silently drift after upload.
    testing_service_id = Column(
        UUID,
        ForeignKey('service.id', ondelete='RESTRICT'),
        nullable=True,
        index=True,
        comment="Resolved Service.id for the executionBackend declared in meta.yaml",
    )

    # Tracking
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(UUID, ForeignKey("user.id"), comment="User who created this version")

    # Relationships
    example = relationship("Example", back_populates="versions")
    created_by_user = relationship("User", foreign_keys=[created_by])
    testing_service = relationship("Service", foreign_keys=[testing_service_id])

    # Deployment tracking

    # Constraints
    __table_args__ = (
        UniqueConstraint("example_id", "version_tag", name="unique_example_version_tag"),
        UniqueConstraint("example_id", "version_number", name="unique_example_version_number"),
    )

    def __repr__(self):
        return f"<ExampleVersion(id={self.id}, version_tag='{self.version_tag}')>"

    @staticmethod
    def extract_execution_backend(meta: dict | None) -> dict | None:
        """Pull ``properties.executionBackend`` out of a parsed meta dict.

        Returns the full block (slug + version + settings) or None.
        Used by the upload path to populate ``execution_backend``.
        """
        if not isinstance(meta, dict):
            return None
        properties = meta.get('properties')
        if not isinstance(properties, dict):
            return None
        eb = properties.get('executionBackend')
        return eb if isinstance(eb, dict) else None

    def get_execution_backend_slug(self) -> str | None:
        """Convenience accessor for the execution-backend slug.

        Reads the dedicated ``execution_backend`` JSONB column — no YAML
        parsing, no nested-dict walking. Prefer the resolved
        ``testing_service_id`` FK for runtime decisions; this method is
        for callers that genuinely need the original slug string (e.g.
        legacy fallbacks where the FK wasn't backfilled).
        """
        if not isinstance(self.execution_backend, dict):
            return None
        return self.execution_backend.get('slug')


class ExampleDependency(Base):
    """
    Dependency relationship between examples with version constraints.
    
    Tracks when one example depends on another with optional version constraints.
    Supports semantic versioning constraints like '>=1.2.0', '^2.1.0', '~1.3.0', etc.
    """
    
    __tablename__ = "example_dependency"
    
    # Primary key
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    
    # Dependency relationship
    example_id = Column(
        UUID, 
        ForeignKey("example.id", ondelete="CASCADE"), 
        nullable=False,
        comment="Example that has the dependency"
    )
    depends_id = Column(
        UUID, 
        ForeignKey("example.id", ondelete="CASCADE"), 
        nullable=False,
        comment="Example that this depends on"
    )
    
    # Version constraint
    version_constraint = Column(
        String(100),
        nullable=True,
        comment="Version constraint (e.g., '>=1.2.0', '^2.1.0', '~1.3.0'). NULL means latest version."
    )
    
    # Tracking
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    example = relationship("Example", foreign_keys=[example_id], back_populates="dependencies")
    dependency = relationship("Example", foreign_keys=[depends_id])
    
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "example_id", "depends_id",
            name="unique_example_dependency"
        ),
    )
    
    def __repr__(self):
        constraint = f", version_constraint='{self.version_constraint}'" if self.version_constraint else ""
        return f"<ExampleDependency(example_id={self.example_id}, depends_id={self.depends_id}{constraint})>"
