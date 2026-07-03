"""add token column to course_git_binding

Revision ID: c9a1b2d3e4f5
Revises: f0a1b2c3d4e5
Create Date: 2026-07-03

Per-course git credential: stores a GitLab group access token on the binding
(encrypted at rest) so an external-GitLab course brings its own credential +
parent group instead of sharing a managed registry server's token. Forgejo is
unaffected (it keeps using the system server token). Nullable — existing
bindings and every Forgejo-backed course keep working untouched.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c9a1b2d3e4f5'
down_revision = 'f0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'course_git_binding',
        sa.Column('token', sa.String(length=4096), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('course_git_binding', 'token')
