"""
SQLAlchemy models for deployment tracking.

This module contains models for tracking the deployment of examples to course content,
separating deployment concerns from the hierarchical course structure.
"""

from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, 
    UniqueConstraint, Index, text, JSON, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
try:
    from ..custom_types import LtreeType
except ImportError:
    # Fallback for Alembic context
    from computor_backend.custom_types import LtreeType
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from .course import CourseContent
    from .example import ExampleVersion
    from .auth import User


class CourseContentDeployment(Base):
    """
    Tracks the deployment of example versions to course content.
    
    This table separates deployment concerns from the CourseContent hierarchy,
    allowing clean tracking of what examples are deployed where.
    Only submittable course content (assignments) should have deployment records.
    """
    
    __tablename__ = "course_content_deployment"
    
    # Primary key
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    
    # Core relationships (what is deployed where)
    course_content_id = Column(
        UUID, 
        ForeignKey("course_content.id", ondelete="CASCADE"),
        nullable=False,
        comment="The course content (assignment) this deployment is for"
    )
    
    example_version_id = Column(
        UUID,
        ForeignKey("example_version.id", ondelete="SET NULL"),
        nullable=True,
        comment="The specific example version that is/was deployed"
    )
    
    # Source identity (supports DB-backed and custom assignments)
    example_identifier = Column(
        LtreeType,
        nullable=True,
        comment="Hierarchical identifier (ltree) of the example source; present even if no DB Example exists"
    )
    version_tag = Column(
        String(64),
        nullable=True,
        comment="Version tag of the example source; may be null for custom assignments"
    )
    
    # Reference commit used for release from assignments repository
    version_identifier = Column(
        String(64),
        nullable=True,
        comment="Commit SHA in assignments repository used for this release"
    )
    
    # Deployment status tracking
    deployment_status = Column(
        String(32),
        nullable=False,
        server_default="pending",
        comment="Status: pending, deploying, deployed, failed, unassigned"
    )
    
    deployment_message = Column(
        Text,
        nullable=True,
        comment="Additional message about deployment (e.g., error details)"
    )
    
    # Deployment timestamps
    assigned_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When the example was assigned to this content"
    )
    
    deployed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the deployment was successfully completed"
    )
    
    last_attempt_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the last deployment attempt was made"
    )
    
    # Git/Repository tracking
    deployment_path = Column(
        Text,
        nullable=True,
        comment="Path in the student-template repository where deployed"
    )
    
    # Deployment metadata
    deployment_metadata = Column(
        JSONB,
        nullable=True,
        server_default=text("'{}'::jsonb"),
        comment="Additional deployment data (workflow IDs, file lists, etc.)"
    )
    
    # Temporal workflow tracking
    workflow_id = Column(
        String(255),
        nullable=True,
        comment="Current/last Temporal workflow ID for deployment"
    )
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID, ForeignKey("user.id", ondelete="SET NULL"))
    updated_by = Column(UUID, ForeignKey("user.id", ondelete="SET NULL"))
    
    # Relationships
    course_content: "CourseContent" = relationship(
        "CourseContent", 
        back_populates="deployment",
        foreign_keys=[course_content_id]
    )
    
    example_version: Optional["ExampleVersion"] = relationship(
        "ExampleVersion",
        foreign_keys=[example_version_id]
    )
    
    created_by_user: Optional["User"] = relationship("User", foreign_keys=[created_by])
    updated_by_user: Optional["User"] = relationship("User", foreign_keys=[updated_by])
    
    # History tracking
    history_entries = relationship(
        "DeploymentHistory",
        back_populates="deployment",
        cascade="all, delete-orphan",
        order_by="DeploymentHistory.created_at.desc()"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # One deployment per course content
        UniqueConstraint("course_content_id", name="uq_deployment_per_content"),
        
        # Indexes for common queries
        Index("idx_deployment_status", "deployment_status"),
        Index("idx_deployment_deployed_at", "deployed_at"),
        Index("idx_deployment_example_version", "example_version_id"),
        Index("idx_deployment_example_identifier", "example_identifier"),
        Index("idx_deployment_version_tag", "version_tag"),
    )
    
    def __repr__(self):
        return f"<CourseContentDeployment(id={self.id}, content={self.course_content_id}, status={self.deployment_status})>"
    
    def set_deploying(self, workflow_id: str = None):
        """Mark deployment as in progress."""
        from datetime import datetime, timezone
        self.deployment_status = "deploying"
        self.last_attempt_at = datetime.now(timezone.utc)
        if workflow_id:
            self.workflow_id = workflow_id
    
    def set_deployed(self, path: str, workflow_id: str = None, metadata: Dict[str, Any] = None):
        """Mark deployment as successful."""
        from datetime import datetime, timezone
        self.deployment_status = "deployed"
        self.deployed_at = datetime.now(timezone.utc)
        self.deployment_path = path
        if workflow_id:
            self.workflow_id = workflow_id
        if metadata:
            if not self.deployment_metadata:
                self.deployment_metadata = {}
            self.deployment_metadata.update(metadata)
    
    def set_failed(self, error_message: str, workflow_id: str = None, metadata: Dict[str, Any] = None):
        """Mark deployment as failed."""
        from datetime import datetime, timezone
        self.deployment_status = "failed"
        self.deployment_message = error_message[:500] if error_message else None  # Truncate long messages
        self.last_attempt_at = datetime.now(timezone.utc)
        if workflow_id:
            self.workflow_id = workflow_id
        if metadata:
            if not self.deployment_metadata:
                self.deployment_metadata = {}
            self.deployment_metadata.update(metadata)


class DeploymentHistory(Base):
    """
    Audit log for deployment changes.
    
    Tracks all changes to deployments including assignments, reassignments,
    deployments, failures, and unassignments.
    """
    
    __tablename__ = "deployment_history"
    
    # Primary key
    id = Column(UUID, primary_key=True, server_default=text("uuid_generate_v4()"))
    
    # Link to deployment
    deployment_id = Column(
        UUID,
        ForeignKey("course_content_deployment.id", ondelete="CASCADE"),
        nullable=False,
        comment="The deployment this history entry belongs to"
    )
    
    # Action tracking
    action = Column(
        String(32),
        nullable=False,
        comment="Action type: assigned, reassigned, deploying, deployed, failed, unassigned, updated"
    )
    
    # Version tracking
    example_version_id = Column(
        UUID,
        ForeignKey("example_version.id", ondelete="SET NULL"),
        nullable=True,
        comment="The example version involved in this action"
    )
    
    previous_example_version_id = Column(
        UUID,
        ForeignKey("example_version.id", ondelete="SET NULL"),
        nullable=True,
        comment="Previous example version (for reassignments)"
    )
    
    # Snapshot of source identity at the time of action
    example_identifier = Column(
        LtreeType,
        nullable=True,
        comment="Hierarchical identifier (ltree) of the example at action time"
    )
    version_tag = Column(
        String(64),
        nullable=True,
        comment="Version tag of the example at action time"
    )
    
    # Workflow tracking
    workflow_id = Column(
        String(255),
        nullable=True,
        comment="Temporal workflow ID if action was triggered by workflow"
    )
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(UUID, ForeignKey("user.id", ondelete="SET NULL"))
    
    # Relationships
    deployment = relationship(
        "CourseContentDeployment",
        back_populates="history_entries"
    )
    
    example_version: Optional["ExampleVersion"] = relationship(
        "ExampleVersion",
        foreign_keys=[example_version_id]
    )
    
    previous_example_version: Optional["ExampleVersion"] = relationship(
        "ExampleVersion",
        foreign_keys=[previous_example_version_id]
    )
    
    created_by_user: Optional["User"] = relationship("User", foreign_keys=[created_by])
    
    # Indexes
    __table_args__ = (
        Index("idx_history_deployment_id", "deployment_id"),
        Index("idx_history_action", "action"),
        Index("idx_history_created_at", "created_at"),
        Index("idx_history_workflow_id", "workflow_id"),
        Index("idx_history_example_identifier", "example_identifier"),
        Index("idx_history_version_tag", "version_tag"),
    )
    
    def __repr__(self):
        return f"<DeploymentHistory(id={self.id}, action={self.action}, deployment={self.deployment_id})>"
