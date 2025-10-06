from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, DateTime, 
    ForeignKey, String, text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class Role(Base):
    __tablename__ = 'role'
    __table_args__ = (
        CheckConstraint("(NOT builtin) OR ((id)::text ~ '^_'::text)"),
        CheckConstraint('(builtin AND ctutor_valid_slug(SUBSTRING(id FROM 2))) OR ((NOT builtin) AND ctutor_valid_slug((id)::text))')
    )

    id = Column(String(255), primary_key=True)
    title = Column(String(255))
    description = Column(String(4096))
    builtin = Column(Boolean, nullable=False, server_default=text("false"))

    # Relationships
    role_claims = relationship('RoleClaim', back_populates='role', cascade='all, delete-orphan')
    user_roles = relationship('UserRole', back_populates='role')


class RoleClaim(Base):
    __tablename__ = 'role_claim'

    role_id = Column(ForeignKey('role.id', ondelete='CASCADE'), primary_key=True, nullable=False)
    claim_type = Column(String(255), primary_key=True, nullable=False)
    claim_value = Column(String(255), primary_key=True, nullable=False)
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    created_by = Column(UUID)
    updated_by = Column(UUID)
    properties = Column(JSONB)

    role = relationship('Role', back_populates='role_claims')


class UserRole(Base):
    __tablename__ = 'user_role'

    user_id = Column(ForeignKey('user.id', ondelete='CASCADE'), primary_key=True, nullable=False)
    role_id = Column(ForeignKey('role.id', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False)
    transient = Column(Boolean, server_default=text("false"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    created_by = Column(UUID)
    updated_by = Column(UUID)

    role = relationship('Role', back_populates='user_roles')
    user = relationship('User', back_populates='user_roles')