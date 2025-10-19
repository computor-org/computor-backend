from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float,
    ForeignKey, Index, Integer, String, text, LargeBinary, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship, Mapped
from typing import TYPE_CHECKING, List

from .base import Base

if TYPE_CHECKING:
    from .course import CourseMember, SubmissionGroup


class SubmissionArtifact(Base):
    """
    Tracks student uploaded submissions with database storage + MinIO tracking.

    This model replaces the use of Result.submit=True for tracking student submissions.
    Each artifact represents a submission version stored as individual files in MinIO.
    Files are stored in the "submissions" bucket at:
    submissions/{submission_group_id}/{version_identifier}/{file_path}
    """
    __tablename__ = 'submission_artifact'
    __table_args__ = (
        Index('submission_artifact_submission_group_idx', 'submission_group_id'),
        Index('submission_artifact_uploaded_by_idx', 'uploaded_by_course_member_id'),
        Index('submission_artifact_uploaded_at_idx', 'uploaded_at'),
        Index('submission_artifact_version_idx', 'version_identifier'),
        Index('submission_artifact_group_version_idx', 'submission_group_id', 'version_identifier'),
        # Note: No unique constraint - allows multiple submissions with same version_identifier
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

    # File information
    content_type = Column(String(120), nullable=True)  # MIME type of the individual file
    file_size = Column(BigInteger, nullable=False)

    # Storage information (MinIO/S3)
    bucket_name = Column(String(255), nullable=False)
    object_key = Column(String(2048), nullable=False)  # Path within the bucket

    # Version tracking
    version_identifier = Column(String(255), nullable=True)  # Git commit hash or version tag

    # Submission flag - indicates if this artifact is an official submission
    # True = official submission counted for grading
    # False = test/practice run, not counted for grading
    submit = Column(Boolean, nullable=False, server_default=text("false"))

    # Metadata and properties
    properties = Column(JSONB, nullable=True)  # Additional metadata

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
    test_results = relationship('Result', back_populates='submission_artifact', cascade='all, delete-orphan')
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
        Index('result_artifact_result_idx', 'result_id'),
        Index('result_artifact_created_at_idx', 'created_at'),
    )

    # Primary key and versioning
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    version = Column(BigInteger, server_default=text("0"))

    # Timestamps
    created_at = Column(DateTime(True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(True), nullable=False, server_default=text("now()"))

    # Foreign keys
    result_id = Column(
        ForeignKey('result.id', ondelete='CASCADE', onupdate='RESTRICT'),
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
    result = relationship('Result', back_populates='result_artifacts')


# TestResult has been removed - we're using the Result model instead
# The Result model in result.py now handles all test execution tracking

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
    status = Column(Integer, nullable=False, server_default=text("0"))  # GradingStatus enum (0=not_reviewed, 1=corrected, 2=correction_necessary, 3=improvement_possible)
    comment = Column(String(4096), nullable=True)  # Grader feedback

    # Relationships
    artifact = relationship('SubmissionArtifact', back_populates='grades')
    graded_by: Mapped["CourseMember"] = relationship(
        'CourseMember',
        back_populates='submission_grades_given',
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
        back_populates='submission_reviews_given',
        foreign_keys=[reviewer_course_member_id]
    )