"""SQLAlchemy models for the private VS Code extension registry."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Extension(Base):
    """Represents a VS Code extension (publisher/name identity)."""

    __tablename__ = "extension"

    id = Column(
        UUID,
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )
    publisher = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    display_name = Column(String(200))
    description = Column(String(2000))

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    versions = relationship(
        "ExtensionVersion",
        back_populates="extension",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("publisher", "name", name="uq_extension_identity"),
        Index("ix_extension_identity", "publisher", "name"),
    )


class ExtensionVersion(Base):
    """Represents a specific published version of an extension."""

    __tablename__ = "extension_version"

    id = Column(
        UUID,
        primary_key=True,

        server_default=text("uuid_generate_v4()"),
    )
    extension_id = Column(
        UUID(as_uuid=True),
        ForeignKey("extension.id", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(String(50), nullable=False)

    version_number = Column(
        Integer,
        nullable=False,
    )

    prerelease = Column(String(100))

    engine_range = Column(String(50))
    yanked = Column(Boolean, default=False, nullable=False)

    size = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False)
    content_type = Column(
        String(100),
        default="application/octet-stream",
        nullable=False,
    )
    object_key = Column(String(512), nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    extension = relationship("Extension", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("extension_id", "version", name="uq_extension_version"),
        UniqueConstraint("extension_id", "version_number", name="uq_extension_version_number"),
        Index(
            "ix_extension_version_order",
            "extension_id",
            "published_at",
            "version_number",
        ),
        Index("ix_extension_version_sha256", "sha256"),
    )
