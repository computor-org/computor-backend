from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float, 
    ForeignKey, Index, Integer, String, text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship, Mapped

from .base import Base


class Result(Base):
    __tablename__ = 'result'
    __table_args__ = (
        Index('result_commit_test_system_key', 'test_system_id', 'execution_backend_id', unique=True),
        # Partial unique indexes - allow multiple results with same version_identifier when status is FAILED(1), CANCELLED(2), or CRASHED(6)
        # Include course_content_id to allow same version for different assignments
        Index('result_version_identifier_member_content_partial_key', 'course_member_id', 'version_identifier', 'course_content_id',
              unique=True, postgresql_where=text('status NOT IN (1, 2, 6)')),
        Index('result_version_identifier_group_content_partial_key', 'submission_group_id', 'version_identifier', 'course_content_id',
              unique=True, postgresql_where=text('status NOT IN (1, 2, 6)'))
    )

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    created_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    updated_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    properties = Column(JSONB)
    submit = Column(Boolean, nullable=False)
    course_member_id = Column(ForeignKey('course_member.id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True)
    submission_group_id = Column(ForeignKey('submission_group.id', ondelete='SET NULL', onupdate='RESTRICT'), index=True)
    course_content_id = Column(ForeignKey('course_content.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False, index=True)
    course_content_type_id = Column(ForeignKey('course_content_type.id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False)
    execution_backend_id = Column(
        ForeignKey('execution_backend.id', ondelete='RESTRICT', onupdate='RESTRICT'),
        nullable=True,
    )
    test_system_id = Column(String(255), nullable=True)
    result = Column(Float(53), nullable=False)
    result_json = Column(JSONB)
    version_identifier = Column(String(2048), nullable=False)
    # Reference commit used for the assignment (from assignments repo)
    reference_version_identifier = Column(String(64), nullable=True)
    status = Column(Integer, nullable=False)

    # Relationships
    course_content: Mapped["CourseContent"] = relationship('CourseContent', back_populates="results", uselist=False, cascade='all,delete')
    course_content_type = relationship('CourseContentType', back_populates='results')
    course_member = relationship('CourseMember', back_populates='results')
    submission_group = relationship('SubmissionGroup', back_populates='results')
    created_by_user = relationship('User', foreign_keys=[created_by])
    updated_by_user = relationship('User', foreign_keys=[updated_by])
    execution_backend = relationship('ExecutionBackend', back_populates='results')
    gradings = relationship('SubmissionGroupGrading', back_populates='result', foreign_keys='SubmissionGroupGrading.result_id')
