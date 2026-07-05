from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Text, text, func
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class PolicyVersion(Base):
    """A privacy-policy / data-processing-notice version.

    Append-only: rows are never updated or deleted. A change to the policy
    text = a new row. The Markdown texts themselves live in MinIO under
    ``policies/{version}/{lang}.md`` (write-once); ``content_hashes`` stores
    a sha256 per language for tamper-evidence.

    The current version is the row with the latest ``effective_from <= now()``.
    """
    __tablename__ = 'policy_versions'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(Text, nullable=False, unique=True, index=True)
    languages = Column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    effective_from = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    content_hashes = Column(JSONB, nullable=True)  # {lang: sha256-hex of the MinIO object}
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserConsent(Base):
    """Auditable record of a user's consent / acknowledgment of a policy version.

    A user has valid consent for a version iff a row exists with that
    ``policy_version`` and ``withdrawn_at IS NULL``. The partial unique index
    makes re-consent idempotent under concurrency.
    """
    __tablename__ = 'user_consents'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    policy_version = Column(ForeignKey('policy_versions.version', ondelete='RESTRICT'), nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(INET, nullable=True)  # proof of consent
    user_agent = Column(Text, nullable=True)  # proof of consent
    purposes = Column(JSONB, nullable=True)  # granular purposes, if any

    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index(
            'user_consents_active_uq',
            'user_id', 'policy_version',
            unique=True,
            postgresql_where=text('withdrawn_at IS NULL'),
        ),
    )

    user = relationship('User', foreign_keys=[user_id])
