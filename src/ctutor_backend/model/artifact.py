from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float,
    ForeignKey, Index, Integer, String, text, LargeBinary
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship, Mapped
from typing import List, TYPE_CHECKING

from .base import Base

if TYPE_CHECKING:
    from .course import CourseMember, SubmissionGroup


class SubmissionArtifact(Base):
    """
    Tracks student uploaded files (submissions) with database storage + MinIO tracking.

    This model replaces the use of Result.submit=True for tracking student submissions.
    Each artifact represents a file that was uploaded by a student as part of their submission.
    """
    __tablename__ = 'submission_artifact'
    __table_args__ = (
        Index('submission_artifact_submission_group_idx', 'submission_group_id'),
        Index('submission_artifact_uploaded_by_idx', 'uploaded_by_course_member_id'),
        Index('submission_artifact_uploaded_at_idx', 'uploaded_at'),
    )

    # Primary key and versioning
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))

    # Timestamps
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    uploaded_at = Column(DateTime(True), nullable=False, server_default=text("now()"))

    # Foreign keys
    submission_group_id = Column(
        ForeignKey('submission_group.id', ondelete='CASCADE', onupdate='RESTRICT'),
        nullable=False
    )
    uploaded_by_course_member_id = Column(
        ForeignKey('course_member.id', ondelete='SET NULL', onupdate='RESTRICT'),
        nullable=True  # Nullable in case the member is removed later
    )

    # File information (removed filename since we upload zip archives)
    content_type = Column(String(120), nullable=True)  # Should typically be 'application/zip'
    file_size = Column(BigInteger, nullable=False)

    # Storage information (MinIO/S3)
    bucket_name = Column(String(255), nullable=False)
    object_key = Column(String(2048), nullable=False)  # Path within the bucket

    # Metadata and properties
    properties = Column(JSONB, nullable=True)  # Additional metadata (version_identifier, etc.)

    # Relationships
    submission_group: Mapped["SubmissionGroup"] = relationship(
        'SubmissionGroup',
        back_populates='submission_artifacts'
    )
    uploaded_by: Mapped["CourseMember"] = relationship(
        'CourseMember',
        back_populates='uploaded_artifacts',
        foreign_keys=[uploaded_by_course_member_id]
    )
    test_results = relationship('TestResult', back_populates='submission_artifact', cascade='all, delete-orphan')
    grades = relationship('SubmissionGrade', back_populates='artifact', cascade='all, delete-orphan')
    reviews = relationship('SubmissionReview', back_populates='artifact', cascade='all, delete-orphan')


class ResultArtifact(Base):
    """
    Tracks files generated from test execution (test output files).

    These are files created during the execution of tests, such as:
    - Test logs
    - Generated reports
    - Debug output
    - Screenshots/artifacts from test runs
    """
    __tablename__ = 'result_artifact'
    __table_args__ = (
        Index('result_artifact_test_result_idx', 'test_result_id'),
        Index('result_artifact_created_at_idx', 'created_at'),
    )

    # Primary key and versioning
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))

    # Timestamps
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))

    # Foreign keys
    test_result_id = Column(
        ForeignKey('test_result.id', ondelete='CASCADE', onupdate='RESTRICT'),
        nullable=False
    )

    # File information (removed filename since results may be archives too)
    content_type = Column(String(120), nullable=True)
    file_size = Column(BigInteger, nullable=False)

    # Storage information (MinIO/S3)
    bucket_name = Column(String(255), nullable=False)
    object_key = Column(String(2048), nullable=False)  # Path within the bucket

    # Metadata
    properties = Column(JSONB, nullable=True)

    # Relationships
    test_result = relationship('TestResult', back_populates='result_artifacts')


class TestResult(Base):
    """
    Tracks test execution results for submission artifacts.

    Replaces the Result model for tracking test executions.
    Each submission artifact can have multiple test results (but typically just one).
    """
    __tablename__ = 'test_result'
    __table_args__ = (
        Index('test_result_submission_artifact_idx', 'submission_artifact_id'),
        Index('test_result_course_member_idx', 'course_member_id'),
        Index('test_result_created_at_idx', 'created_at'),
        # Unique constraint to prevent multiple tests of same artifact by same member (unless failed/cancelled/crashed)
        Index('test_result_unique_success', 'submission_artifact_id', 'course_member_id',
              unique=True, postgresql_where=text('status NOT IN (1, 2, 6)')),
    )

    # Primary key and versioning
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))

    # Timestamps
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    started_at = Column(DateTime(True), nullable=True)
    finished_at = Column(DateTime(True), nullable=True)

    # Foreign keys
    submission_artifact_id = Column(
        ForeignKey('submission_artifact.id', ondelete='CASCADE', onupdate='RESTRICT'),
        nullable=False
    )
    course_member_id = Column(
        ForeignKey('course_member.id', ondelete='RESTRICT', onupdate='RESTRICT'),
        nullable=False
    )
    execution_backend_id = Column(
        ForeignKey('execution_backend.id', ondelete='RESTRICT', onupdate='RESTRICT'),
        nullable=True
    )

    # Test execution data
    test_system_id = Column(String(255), nullable=True)
    status = Column(Integer, nullable=False)  # Same status enum as Result
    result = Column(Float(53), nullable=True)  # Test result as percentage (0.0 to 1.0)

    # Test results and metadata
    result_json = Column(JSONB, nullable=True)  # Detailed test results
    properties = Column(JSONB, nullable=True)  # Additional metadata
    log_text = Column(String, nullable=True)  # Test execution logs

    # Version information
    version_identifier = Column(String(2048), nullable=True)
    reference_version_identifier = Column(String(64), nullable=True)

    # Relationships
    submission_artifact = relationship('SubmissionArtifact', back_populates='test_results')
    course_member: Mapped["CourseMember"] = relationship('CourseMember', back_populates='test_results')
    execution_backend = relationship('ExecutionBackend', back_populates='test_results')
    result_artifacts = relationship('ResultArtifact', back_populates='test_result', cascade='all, delete-orphan')


class SubmissionGrade(Base):
    """
    Tracks grading information for submission artifacts.

    Multiple grades per artifact are allowed (e.g., different graders, re-grading).
    """
    __tablename__ = 'submission_grade'
    __table_args__ = (
        Index('submission_grade_artifact_idx', 'artifact_id'),
        Index('submission_grade_grader_idx', 'graded_by_course_member_id'),
        Index('submission_grade_graded_at_idx', 'graded_at'),
    )

    # Primary key and versioning
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))

    # Timestamps
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    graded_at = Column(DateTime(True), nullable=False, server_default=text("now()"))

    # Foreign keys
    artifact_id = Column(
        ForeignKey('submission_artifact.id', ondelete='CASCADE', onupdate='RESTRICT'),
        nullable=False
    )
    graded_by_course_member_id = Column(
        ForeignKey('course_member.id', ondelete='RESTRICT', onupdate='RESTRICT'),
        nullable=False
    )

    # Grading data
    grade = Column(Float(53), nullable=False)  # Grade as percentage (0.0 to 1.0)
    rubric = Column(JSONB, nullable=True)  # Structured rubric data
    comment = Column(String(4096), nullable=True)  # Grader feedback

    # Relationships
    artifact = relationship('SubmissionArtifact', back_populates='grades')
    graded_by: Mapped["CourseMember"] = relationship(
        'CourseMember',
        back_populates='artifact_grades_given',
        foreign_keys=[graded_by_course_member_id]
    )


class SubmissionReview(Base):
    """
    Tracks review/feedback for submission artifacts.

    Multiple reviews per artifact are allowed (peer review, instructor feedback, etc.).
    """
    __tablename__ = 'submission_review'
    __table_args__ = (
        Index('submission_review_artifact_idx', 'artifact_id'),
        Index('submission_review_reviewer_idx', 'reviewer_course_member_id'),
        Index('submission_review_created_at_idx', 'created_at'),
    )

    # Primary key and versioning
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))

    # Timestamps
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))

    # Foreign keys
    artifact_id = Column(
        ForeignKey('submission_artifact.id', ondelete='CASCADE', onupdate='RESTRICT'),
        nullable=False
    )
    reviewer_course_member_id = Column(
        ForeignKey('course_member.id', ondelete='RESTRICT', onupdate='RESTRICT'),
        nullable=False
    )

    # Review data
    body = Column(String(4096), nullable=False)  # Review text
    review_type = Column(String(50), nullable=True)  # e.g., 'peer', 'instructor', 'automated'

    # Relationships
    artifact = relationship('SubmissionArtifact', back_populates='reviews')
    reviewer: Mapped["CourseMember"] = relationship(
        'CourseMember',
        back_populates='artifact_reviews_given',
        foreign_keys=[reviewer_course_member_id]
    )