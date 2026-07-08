from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declared_attr, relationship

Base = declarative_base()
metadata = Base.metadata


class UUIDPkMixin:
    """UUID primary key with a server-side ``uuid_generate_v4()`` default."""

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))


class VersionedMixin:
    """Optimistic-concurrency ``version`` counter (nullable, server default 0).

    Note: some tables declare ``version`` as ``NOT NULL`` (e.g. the service and
    api_token tables). Those keep their column inline and do NOT use this mixin.
    """

    version = Column(BigInteger, server_default=text("0"))


class AuditMixin:
    """Standard audit block: ``created_at`` / ``updated_at`` timestamps,
    ``created_by`` / ``updated_by`` FKs to ``user.id`` (ON DELETE SET NULL),
    and the matching ``created_by_user`` / ``updated_by_user`` relationships.

    Everything is declared via ``@declared_attr`` so each mapped class receives
    its own Column / relationship objects. The relationship ``foreign_keys`` are
    late-bound with lambdas so each class binds to its OWN ``created_by`` /
    ``updated_by`` column (both point at ``user.id``, so they must be
    disambiguated per-class).

    ``properties`` is intentionally NOT part of this mixin: it is absent on some
    audited tables and differs (nullable / server_default) on others, so it is
    left inline.
    """

    @declared_attr
    def created_at(cls):
        return Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @declared_attr
    def updated_at(cls):
        return Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @declared_attr
    def created_by(cls):
        return Column(ForeignKey('user.id', ondelete='SET NULL'))

    @declared_attr
    def updated_by(cls):
        return Column(ForeignKey('user.id', ondelete='SET NULL'))

    @declared_attr
    def created_by_user(cls):
        return relationship('User', foreign_keys=lambda: [cls.created_by])

    @declared_attr
    def updated_by_user(cls):
        return relationship('User', foreign_keys=lambda: [cls.updated_by])
