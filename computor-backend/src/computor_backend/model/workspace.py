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
from sqlalchemy import BigInteger, CheckConstraint, Column, String, UniqueConstraint, text
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
