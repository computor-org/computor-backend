from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float,
    ForeignKey, Index, Integer, String, text
, func)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship, Mapped
from typing import TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .artifact import SubmissionArtifact, ResultArtifact
    from .course import CourseContent, CourseContentType, CourseMember, SubmissionGroup, SubmissionGroupGrading
    from .auth import User


class Result(Base):
    __tablename__ = 'result'
    __table_args__ = (
        # Partial unique indexes - allow multiple results with same version_identifier when status is FAILED(1), CANCELLED(2), or CRASHED(6)
        # Include course_content_id to allow same version for different assignments
        Index('result_version_identifier_member_content_partial_key', 'course_member_id', 'version_identifier', 'course_content_id',
              unique=True, postgresql_where=text('status NOT IN (1, 2, 6)')),
        Index('result_version_identifier_group_content_partial_key', 'submission_group_id', 'version_identifier', 'course_content_id',
              unique=True, postgresql_where=text('status NOT IN (1, 2, 6)')),
        # New indexes from TestResult for artifact-based testing
        Index('result_submission_artifact_idx', 'submission_artifact_id'),
        Index('result_created_at_idx', 'created_at'),
        # Prevent multiple successful tests of same artifact by same member
        Index('result_artifact_unique_success', 'submission_artifact_id', 'course_member_id',
              unique=True, postgresql_where=text('status NOT IN (1, 2, 6)'))
    )

    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    updated_by = Column(ForeignKey('user.id', ondelete='SET NULL'))
    properties = Column(JSONB)

    # Foreign keys
    course_member_id = Column(ForeignKey('course_member.id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False, index=True)
    submission_artifact_id = Column(ForeignKey('submission_artifact.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=True)
    submission_group_id = Column(ForeignKey('submission_group.id', ondelete='SET NULL', onupdate='RESTRICT'), index=True)
    course_content_id = Column(ForeignKey('course_content.id', ondelete='CASCADE', onupdate='RESTRICT'), nullable=False, index=True)
    course_content_type_id = Column(ForeignKey('course_content_type.id', ondelete='RESTRICT', onupdate='RESTRICT'), nullable=False)

    # Testing service - which service executed this test
    testing_service_id = Column(
        UUID,
        ForeignKey('service.id', ondelete='RESTRICT'),
        nullable=True,
        index=True
    )

    test_system_id = Column(String(255), nullable=True)
    # Test execution data
    grade = Column(Float(53), nullable=True)  # Grade as percentage (0.0 to 1.0)
    result = Column(Float(53), nullable=True)  # Deprecated alias for grade, kept for backward compatibility
    # result_json moved to MinIO storage: results/{result_id}/result.json
    # log_text removed - use application logging instead
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
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
    testing_service = relationship('Service', foreign_keys=[testing_service_id])
    # Gradings moved to SubmissionGrade tied to artifacts

    # New artifact relationships
    submission_artifact: Mapped["SubmissionArtifact"] = relationship('SubmissionArtifact', back_populates='test_results')
    result_artifacts = relationship('ResultArtifact', back_populates='result', cascade='all, delete-orphan')
