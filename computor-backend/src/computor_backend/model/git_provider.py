from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class GitProvider(Base):
    __tablename__ = 'git_provider'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    updated_by = Column(ForeignKey('user.id', ondelete='SET NULL'))

    organization_id = Column(
        ForeignKey('organization.id', ondelete='CASCADE', onupdate='RESTRICT'),
        nullable=False,
        index=True,
    )
    type = Column(String(50), nullable=False)   # 'gitlab' | 'forgejo' | 'github'
    url = Column(String(2048), nullable=False)
    token = Column(String(4096), nullable=False)  # encrypted with keycove

    organization = relationship('Organization', back_populates='git_providers')
    created_by_user = relationship('User', foreign_keys=[created_by])
    updated_by_user = relationship('User', foreign_keys=[updated_by])
