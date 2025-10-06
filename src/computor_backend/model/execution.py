from sqlalchemy import (
    BigInteger, CheckConstraint, Column, DateTime, 
    ForeignKey, String, text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class ExecutionBackend(Base):
    __tablename__ = 'execution_backend'
    __table_args__ = (
        CheckConstraint("(slug)::text ~* '^[A-Za-z0-9_-]+$'::text"),
    )

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    created_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    updated_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    properties = Column(JSONB)
    type = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True)

    # Relationships
    created_by_user = relationship('User', foreign_keys=[created_by])
    updated_by_user = relationship('User', foreign_keys=[updated_by])
    course_execution_backends = relationship('CourseExecutionBackend', back_populates='execution_backend')
    course_contents = relationship('CourseContent', back_populates='execution_backend')
    results = relationship('Result', back_populates='execution_backend')