"""SQLAlchemy models for the private VS Code extension registry."""

from datetime import datetime

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
)
from sqlalchemy.orm import relationship

from .base import Base


class Extension(Base):
    """Represents a VS Code extension (publisher/name identity)."""

    __tablename__ = "extension"

    id = Column(Integer, primary_key=True)
    publisher = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    display_name = Column(String(200))
    description = Column(String(2000))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

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

    id = Column(Integer, primary_key=True)
    extension_id = Column(
        Integer,
        ForeignKey("extension.id", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(String(50), nullable=False)

    semver_major = Column(Integer, nullable=False)
    semver_minor = Column(Integer, nullable=False)
    semver_patch = Column(Integer, nullable=False)
    prerelease = Column(String(100))
    build = Column(String(100))

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

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    published_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    extension = relationship("Extension", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("extension_id", "version", name="uq_extension_version"),
        Index(
            "ix_extension_version_order",
            "extension_id",
            "semver_major",
            "semver_minor",
            "semver_patch",
            "prerelease",
        ),
        Index("ix_extension_version_sha256", "sha256"),
    )
