from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, DateTime, 
    Enum, ForeignKey, String, text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class Group(Base):
    __tablename__ = 'group'
    __table_args__ = (
        CheckConstraint('ctutor_valid_slug((slug)::text)'),
    )

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    created_by = Column(UUID)
    updated_by = Column(UUID)
    properties = Column(JSONB)
    title = Column(String(255))
    description = Column(String(4096))
    slug = Column(String(255), nullable=False)
    type = Column(Enum('fixed', 'dynamic', name='ctutor_group_type'), server_default=text("'fixed'::ctutor_group_type"))

    # Relationships
    group_claims = relationship('GroupClaim', back_populates='group', cascade='all, delete-orphan')
    user_groups = relationship('UserGroup', back_populates='group')


class GroupClaim(Base):
    __tablename__ = 'group_claim'

    group_id = Column(ForeignKey('group.id', ondelete='CASCADE'), primary_key=True, nullable=False)
    claim_type = Column(String(255), primary_key=True, nullable=False)
    claim_value = Column(String(255), primary_key=True, nullable=False)
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    created_by = Column(UUID)
    updated_by = Column(UUID)
    properties = Column(JSONB)

    group = relationship('Group', back_populates='group_claims')


class UserGroup(Base):
    __tablename__ = 'user_group'

    user_id = Column(ForeignKey('user.id', ondelete='CASCADE'), primary_key=True, nullable=False)
    group_id = Column(ForeignKey('group.id', ondelete='RESTRICT', onupdate='CASCADE'), primary_key=True, nullable=False)
    transient = Column(Boolean, server_default=text("false"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    created_by = Column(UUID)
    updated_by = Column(UUID)

    group = relationship('Group', back_populates='user_groups')
    user = relationship('User', back_populates='user_groups')