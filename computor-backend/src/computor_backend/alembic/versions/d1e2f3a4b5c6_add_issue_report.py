"""Store who filed which problem report, apart from the issue itself

Issue #212. A problem report becomes a GitHub issue, but the reporter's
identity is deliberately not part of it — the issue carries only the opaque
report id, so anyone with access to the tracker cannot tell who complained.
This table is the join, read through an admin-only lookup.

Nothing the user wrote is stored here: the prose lives in the GitHub issue and
only there, so there is a single place to redact from.

``user_id`` is ON DELETE SET NULL rather than CASCADE. Erasing a user has to
remove the link to them, but the issue outlives the account and a row recording
that a report happened stays useful once it can no longer identify anybody.

Revision ID: d1e2f3a4b5c6
Revises: c8d4e5f6a7b2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'd1e2f3a4b5c6'
down_revision = 'c8d4e5f6a7b2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'issue_report',
        sa.Column(
            'id',
            postgresql.UUID(),
            server_default=sa.text('uuid_generate_v4()'),
            nullable=False,
        ),
        sa.Column('user_id', postgresql.UUID(), nullable=True),
        sa.Column('repository', sa.Text(), nullable=False),
        sa.Column('issue_number', sa.Integer(), nullable=True),
        sa.Column('issue_url', sa.Text(), nullable=True),
        sa.Column(
            'submitted_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_issue_report_user_id', 'issue_report', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_issue_report_user_id', table_name='issue_report')
    op.drop_table('issue_report')
