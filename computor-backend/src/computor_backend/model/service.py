"""
Service and API Token models for service account management.

Service accounts are specialized users (is_service=true) that represent
automated workers, integrations, and other non-human systems.

Service users typically authenticate via API tokens, but can optionally
have passwords for administrative access or debugging purposes.

API tokens provide scoped authentication for both service and regular users.

ServiceType defines the types of services available in the system using
UUID + Ltree hybrid approach for stable references and hierarchical organization.
"""

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, DateTime,
    ForeignKey, Index, LargeBinary, String, Text, func, text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

try:
    from ..custom_types import LtreeType
except ImportError:
    from computor_backend.custom_types import LtreeType

from .base import Base


class ServiceType(Base):
    """
    Service type definitions with hierarchical organization.

    Combines UUID primary keys (stable FK references) with Ltree paths
    (human-readable hierarchical organization).

    Service types define what kinds of services exist in the system:
    - testing.* (code testing services: python, matlab, cpp, java)
    - review.* (content review services: llm, latex)
    - worker.* (task queue workers: temporal)
    - metrics.* (analytics and monitoring)
    - integration.* (external system integrations: gitlab, github)

    The hierarchical path structure enables:
    - Natural categorization (testing.python, testing.matlab)
    - Plugin namespacing (vendor.product.service)
    - Efficient queries (all testing services, all LLM reviewers)
    - Self-documenting structure

    Examples:
        testing.python (UUID: 123e4567-...)
        testing.matlab (UUID: 987fcdeb-...)
        review.llm.gpt4 (UUID: abcd1234-...)
        worker.temporal (UUID: def45678-...)
        acme.grading.java (UUID: 789abcde-..., third-party plugin)
    """
    __tablename__ = 'service_type'
    __table_args__ = (
        CheckConstraint(
            "path::text ~ '^[A-Za-z0-9_-]+(\\.[A-Za-z0-9_-]+)*$'",
            name='ck_service_type_path_format'
        ),
        Index('idx_service_type_path_gist', 'path', postgresql_using='gist'),
        Index('idx_service_type_category', 'category'),
        Index('idx_service_type_enabled', 'enabled', postgresql_where=text("enabled = true")),
        Index('idx_service_type_plugin_module', 'plugin_module', postgresql_where=text("plugin_module IS NOT NULL")),
    )

    # Primary key (UUID for stable FK references)
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, nullable=False, server_default=text("0"))

    # Unique hierarchical path (Ltree for organization and queries)
    path = Column(LtreeType, unique=True, nullable=False)

    # Display information
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Categorization (derived from path root, but indexed for performance)
    # Categories: 'worker', 'testing', 'review', 'metrics', 'integration'
    category = Column(String(63), nullable=False)

    # Plugin system
    plugin_module = Column(String(255))  # Python module path providing functionality

    # JSON Schema for validating Service.config
    # Defines what configuration options are valid for services of this type
    schema = Column(JSONB)

    # UI/UX
    icon = Column(String(255))  # Icon identifier for UI
    color = Column(String(7))  # Hex color for UI (e.g., #FF5733)

    # Status
    enabled = Column(Boolean, nullable=False, server_default=text("true"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Audit fields
    created_by = Column(UUID, ForeignKey('user.id', ondelete='SET NULL'))
    updated_by = Column(UUID, ForeignKey('user.id', ondelete='SET NULL'))

    # Additional properties
    properties = Column(JSONB, server_default=text("'{}'::jsonb"), nullable=False)

    # Relationships
    services = relationship('Service', foreign_keys='Service.service_type_id', back_populates='service_type_rel')
    created_by_user = relationship('User', foreign_keys=[created_by])
    updated_by_user = relationship('User', foreign_keys=[updated_by])

    def __repr__(self):
        return f"<ServiceType(id={self.id}, path='{self.path}', name='{self.name}')>"


class Service(Base):
    """
    Service account metadata for automated workers and integrations.

    Each service has a 1-to-1 relationship with a User where is_service=true.
    The User provides authentication and authorization, while Service provides
    service-specific metadata and configuration.

    Examples:
        - temporal-worker-python: Temporal worker for Python test execution
        - temporal-worker-matlab: Temporal worker for MATLAB test execution
        - grading-service: Automated grading worker
        - notification-service: Email/notification daemon
    """
    __tablename__ = 'service'
    __table_args__ = (
        CheckConstraint(
            "slug ~* '^[a-z0-9][a-z0-9-]*[a-z0-9]$'",
            name='ck_service_slug_format'
        ),
        Index('idx_service_enabled', 'enabled', postgresql_where=text("enabled = true AND archived_at IS NULL")),
    )

    # Primary key and versioning
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, nullable=False, server_default=text("0"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Audit fields
    created_by = Column(UUID, ForeignKey('user.id', ondelete='SET NULL'))
    updated_by = Column(UUID, ForeignKey('user.id', ondelete='SET NULL'))

    # Soft delete
    archived_at = Column(DateTime(timezone=True))

    # Additional properties
    properties = Column(JSONB)

    # Service identification
    slug = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Service Type (UUID FK to service_type table)
    service_type_id = Column(
        UUID,
        ForeignKey('service_type.id', ondelete='RESTRICT'),
        nullable=True,
        index=True
    )

    # 1-to-1 relationship with user (service account)
    user_id = Column(
        UUID,
        ForeignKey('user.id', ondelete='RESTRICT'),
        nullable=False,
        unique=True
    )

    # Service-specific configuration
    config = Column(JSONB, server_default=text("'{}'::jsonb"))

    # Status tracking
    enabled = Column(Boolean, nullable=False, server_default=text("true"))
    last_seen_at = Column(DateTime(timezone=True))

    # Relationships
    service_type_rel = relationship('ServiceType', foreign_keys=[service_type_id], back_populates='services')
    user = relationship('User', foreign_keys=[user_id], back_populates='service')
    created_by_user = relationship('User', foreign_keys=[created_by])
    updated_by_user = relationship('User', foreign_keys=[updated_by])


class ApiToken(Base):
    """
    API tokens for authentication with scoped permissions.

    API tokens provide an alternative to password-based authentication,
    with fine-grained scope control and usage tracking.

    Token format: ctp_<random_32_chars>
    Example: ctp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

    The token is hashed (SHA-256) before storage for security.
    Only the prefix (first 12 chars) is stored in plaintext for identification.
    """
    __tablename__ = 'api_token'
    __table_args__ = (
        CheckConstraint(
            "(expires_at IS NULL) OR (expires_at > created_at)",
            name='ck_api_token_expiration'
        ),
        Index('idx_api_token_user_active', 'user_id', postgresql_where=text("revoked_at IS NULL")),
        Index('idx_api_token_prefix', 'token_prefix'),
        Index('idx_api_token_hash_active', 'token_hash', postgresql_where=text("revoked_at IS NULL")),
    )

    # Primary key and versioning
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, nullable=False, server_default=text("0"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Audit fields
    created_by = Column(UUID, ForeignKey('user.id', ondelete='SET NULL'))
    updated_by = Column(UUID, ForeignKey('user.id', ondelete='SET NULL'))

    # Token identification
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Token owner
    user_id = Column(
        UUID,
        ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Token value (hashed for security)
    token_hash = Column(LargeBinary, nullable=False, unique=True)
    token_prefix = Column(String(12), nullable=False)

    # Scopes define what the token can access
    # Format: ["read:courses", "write:results", "execute:tests"]
    scopes = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))

    # Expiration and usage tracking
    expires_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    usage_count = Column(BigInteger, nullable=False, server_default=text("0"))

    # Revocation
    revoked_at = Column(DateTime(timezone=True))
    revocation_reason = Column(Text)

    # Additional metadata
    properties = Column(JSONB)

    # Relationships
    user = relationship('User', foreign_keys=[user_id], back_populates='api_tokens')
    created_by_user = relationship('User', foreign_keys=[created_by])
    updated_by_user = relationship('User', foreign_keys=[updated_by])
