"""Coder workspace template settings.

Coder (plus the ``template.json`` manifests on disk) stays the source of
truth for which workspace templates *exist* — see ``coder/`` and
``tasks/temporal_coder_setup.py``. This table only carries the per-template
knobs Computor owns:

- container resource caps (``memory_mb`` / ``cpu_shares``) applied as
  ``--variable`` values at template push time, and
- the ``max_running_workspaces`` quota enforced at provision/start time, and
- extra Terraform variable overrides pushed the same way.

Keyed by the Coder template name (e.g. ``vscode-workspace``) so a row
survives template re-pushes and the ``.computor-managed`` re-sync of the
template files. Rows are deliberately NOT written into the Terraform files:
that would flip the template to operator-customized and cut it off from
repo updates just to set a memory cap.
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base, UUIDPkMixin, VersionedMixin, AuditMixin


class WorkspaceTemplateSettings(UUIDPkMixin, VersionedMixin, AuditMixin, Base):
    """Per-template resource limits, quota, and Terraform variable overrides."""

    __tablename__ = 'workspace_template_settings'
    __table_args__ = (
        UniqueConstraint('template_name', name='workspace_template_settings_name_key'),
        CheckConstraint('memory_mb IS NULL OR memory_mb >= 0',
                        name='workspace_template_settings_memory_check'),
        CheckConstraint('cpu_shares IS NULL OR cpu_shares >= 0',
                        name='workspace_template_settings_cpu_check'),
        CheckConstraint('max_running_workspaces IS NULL OR max_running_workspaces >= 0',
                        name='workspace_template_settings_quota_check'),
    )

    # Coder template name ("vscode-workspace"); matches CoderTemplate.name and
    # the manifest's coder_template_name, NOT the template directory name.
    template_name = Column(String(255), nullable=False)
    # Disabled templates are hidden from non-manager listings and cannot be
    # provisioned by non-managers (workspace:manage may still provision, to
    # test before enabling). Existing workspaces keep starting — a hard freeze
    # is max_running_workspaces = 0.
    enabled = Column(Boolean, nullable=False, server_default=text('true'))
    # Container caps, pushed as Terraform --variable memory_mb / cpu_shares.
    # NULL (or 0) = unlimited / Docker default — the variable is then simply
    # not passed and the template's own default (0) applies.
    memory_mb = Column(BigInteger)
    cpu_shares = Column(BigInteger)
    # Max concurrently running/starting workspaces of this template across ALL
    # users (e.g. MATLAB license seats). NULL = unlimited; 0 freezes the
    # template. Enforced for everyone, admins included.
    max_running_workspaces = Column(BigInteger)
    # Extra Terraform variable overrides ({name: value}) pushed with the same
    # declared-variable guard as the deployment-wide template_variables.
    template_variables = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))


class CourseWorkspaceTemplate(UUIDPkMixin, VersionedMixin, AuditMixin, Base):
    """A workspace template allowed in a course.

    Grants the course's members course-derived workspace access (list,
    self-provision, own start/stop) for the template without any global
    workspace role. ``template_name`` is deliberately NOT an FK to
    ``workspace_template_settings`` — settings rows are lazily upserted and
    may not exist for a template that Coder serves.
    """

    __tablename__ = 'course_workspace_template'
    __table_args__ = (
        UniqueConstraint('course_id', 'template_name',
                         name='course_workspace_template_key'),
    )

    course_id = Column(
        ForeignKey('course.id', ondelete='CASCADE', onupdate='RESTRICT'),
        nullable=False,
    )
    # Coder template name, same identity as WorkspaceTemplateSettings.template_name.
    template_name = Column(String(255), nullable=False)


class CourseWorkspaceSettings(UUIDPkMixin, VersionedMixin, AuditMixin, Base):
    """Course-level workspace flags, governed by workspace:manage.

    Separate from the per-template join rows: these are course-wide switches.
    """

    __tablename__ = 'course_workspace_settings'
    __table_args__ = (
        UniqueConstraint('course_id', name='course_workspace_settings_course_key'),
    )

    course_id = Column(
        ForeignKey('course.id', ondelete='CASCADE', onupdate='RESTRICT'),
        nullable=False,
    )
    # Whether course lecturers may bulk-provision (throwaway) workspaces for
    # the course's students.
    lecturer_provision_enabled = Column(Boolean, nullable=False, server_default=text('false'))
