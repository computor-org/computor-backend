import secrets
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class InviteLink(Base):
    __tablename__ = 'invite_link'

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)

    token = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(320), nullable=True)  # if set, only this email may accept
    max_uses = Column(Integer, nullable=False, server_default=text("1"))
    use_count = Column(Integer, nullable=False, server_default=text("0"))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    roles = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # list of role_ids
    note = Column(Text, nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    creator = relationship('User', foreign_keys=[created_by])

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)
