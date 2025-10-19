from sqlalchemy import (
    BigInteger, CheckConstraint, Column, DateTime, 
    Enum, ForeignKey, Index, String, text, Computed
, func)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
try:
    from ..custom_types import LtreeType
except ImportError:
    # Fallback for Alembic context
    from computor_backend.custom_types import LtreeType

from .base import Base


class Organization(Base):
    __tablename__ = 'organization'
    __table_args__ = (
        CheckConstraint("((organization_type = 'user'::organization_type) AND (title IS NULL)) OR ((organization_type <> 'user'::organization_type) AND (title IS NOT NULL))"),
        CheckConstraint("((organization_type = 'user'::organization_type) AND (user_id IS NOT NULL)) OR ((organization_type <> 'user'::organization_type) AND (user_id IS NULL))"),
        Index('organization_path_key', 'organization_type', 'path', unique=True),
        Index('organization_number_key', 'organization_type', 'number', unique=True)
    )

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    updated_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    properties = Column(JSONB)
    number = Column(String(255))
    title = Column(String(255))
    description = Column(String(4096))
    archived_at = Column(DateTime(timezone=True))
    email = Column(String(320))
    telephone = Column(String(255))
    fax_number = Column(String(255))
    url = Column(String(2048))
    postal_code = Column(String(255))
    street_address = Column(String(1024))
    locality = Column(String(255))
    region = Column(String(255))
    country = Column(String(255))
    organization_type = Column(Enum('user', 'community', 'organization', name='organization_type'), nullable=False, index=True)
    user_id = Column(ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'), unique=True)
    path = Column(LtreeType, nullable=False, index=True)
    parent_path = Column(LtreeType, Computed('''
        CASE
            WHEN (nlevel(path) > 1) THEN subpath(path, 0, (nlevel(path) - 1))
            ELSE NULL::ltree
        END
    ''', persisted=True))

    # Relationships
    created_by_user = relationship('User', foreign_keys=[created_by])
    updated_by_user = relationship('User', foreign_keys=[updated_by])
    user = relationship('User', foreign_keys=[user_id], back_populates='organization')
    course_families = relationship('CourseFamily', back_populates='organization', uselist=True, lazy='select')
    courses = relationship('Course', back_populates='organization', uselist=True, lazy='select')
    example_repositories = relationship('ExampleRepository', back_populates='organization', uselist=True, lazy='select')
    student_profiles = relationship('StudentProfile', back_populates='organization', uselist=True, lazy='select')