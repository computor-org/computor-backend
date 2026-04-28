"""add scoped roles for organization and course_family

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-04-26 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add per-organization and per-course-family scoped role tables.

    Mirrors the existing course_role / course_member pattern. Seeds two
    built-in roles per scope: _owner, _manager. _owner > _manager in
    hierarchy. Roles only grant write/admin privileges on the scope
    itself; read visibility continues to use the course-membership
    cascade — these roles do not cascade up or down.
    """
    # organization_role
    op.create_table(
        'organization_role',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('title', sa.String(255)),
        sa.Column('description', sa.String(4096)),
        sa.Column('builtin', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.CheckConstraint("(NOT builtin) OR ((id)::text ~ '^_'::text)"),
        sa.CheckConstraint(
            "(builtin AND computor_valid_slug(SUBSTRING(id FROM 2))) "
            "OR ((NOT builtin) AND computor_valid_slug((id)::text))"
        ),
    )

    # organization_member
    op.create_table(
        'organization_member',
        sa.Column(
            'id', sa.dialects.postgresql.UUID(as_uuid=False),
            primary_key=True, server_default=sa.text('uuid_generate_v4()'),
        ),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0')),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            'created_by', sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey('user.id', ondelete='SET NULL'),
        ),
        sa.Column(
            'updated_by', sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey('user.id', ondelete='SET NULL'),
        ),
        sa.Column('properties', sa.dialects.postgresql.JSONB()),
        sa.Column(
            'user_id', sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'),
            nullable=False,
        ),
        sa.Column(
            'organization_id', sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey('organization.id', ondelete='CASCADE', onupdate='RESTRICT'),
            nullable=False,
        ),
        sa.Column(
            'organization_role_id', sa.String(255),
            sa.ForeignKey('organization_role.id', ondelete='RESTRICT', onupdate='RESTRICT'),
            nullable=False,
        ),
    )
    op.create_index(
        'organization_member_user_org_key',
        'organization_member',
        ['user_id', 'organization_id'],
        unique=True,
    )
    op.create_index(
        'ix_organization_member_organization_id',
        'organization_member',
        ['organization_id'],
    )

    # course_family_role
    op.create_table(
        'course_family_role',
        sa.Column('id', sa.String(255), primary_key=True),
        sa.Column('title', sa.String(255)),
        sa.Column('description', sa.String(4096)),
        sa.Column('builtin', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.CheckConstraint("(NOT builtin) OR ((id)::text ~ '^_'::text)"),
        sa.CheckConstraint(
            "(builtin AND computor_valid_slug(SUBSTRING(id FROM 2))) "
            "OR ((NOT builtin) AND computor_valid_slug((id)::text))"
        ),
    )

    # course_family_member
    op.create_table(
        'course_family_member',
        sa.Column(
            'id', sa.dialects.postgresql.UUID(as_uuid=False),
            primary_key=True, server_default=sa.text('uuid_generate_v4()'),
        ),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0')),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            'created_by', sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey('user.id', ondelete='SET NULL'),
        ),
        sa.Column(
            'updated_by', sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey('user.id', ondelete='SET NULL'),
        ),
        sa.Column('properties', sa.dialects.postgresql.JSONB()),
        sa.Column(
            'user_id', sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey('user.id', ondelete='CASCADE', onupdate='RESTRICT'),
            nullable=False,
        ),
        sa.Column(
            'course_family_id', sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey('course_family.id', ondelete='CASCADE', onupdate='RESTRICT'),
            nullable=False,
        ),
        sa.Column(
            'course_family_role_id', sa.String(255),
            sa.ForeignKey('course_family_role.id', ondelete='RESTRICT', onupdate='RESTRICT'),
            nullable=False,
        ),
    )
    op.create_index(
        'course_family_member_user_family_key',
        'course_family_member',
        ['user_id', 'course_family_id'],
        unique=True,
    )
    op.create_index(
        'ix_course_family_member_course_family_id',
        'course_family_member',
        ['course_family_id'],
    )

    # Seed builtin roles. Three-level hierarchy: owner > manager > developer.
    #   _developer  → can read and edit the scope; cannot assign roles
    #   _manager    → can edit and assign roles, except cannot assign _owner
    #   _owner      → full control: edit, delete/archive, assign any role
    op.execute("""
        INSERT INTO organization_role (id, title, description, builtin) VALUES
            ('_owner',     'Owner',     'Full control: edit, delete/archive, assign any role.', true),
            ('_manager',   'Manager',   'Edit and assign roles (except _owner).',               true),
            ('_developer', 'Developer', 'Edit the organization but cannot assign roles.',       true)
        ON CONFLICT (id) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO course_family_role (id, title, description, builtin) VALUES
            ('_owner',     'Owner',     'Full control: edit, delete/archive, assign any role.', true),
            ('_manager',   'Manager',   'Edit and assign roles (except _owner).',               true),
            ('_developer', 'Developer', 'Edit the course family but cannot assign roles.',      true)
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    """Drop scoped role tables (best-effort; data is destroyed)."""
    op.drop_index('ix_course_family_member_course_family_id', table_name='course_family_member')
    op.drop_index('course_family_member_user_family_key', table_name='course_family_member')
    op.drop_table('course_family_member')
    op.drop_table('course_family_role')

    op.drop_index('ix_organization_member_organization_id', table_name='organization_member')
    op.drop_index('organization_member_user_org_key', table_name='organization_member')
    op.drop_table('organization_member')
    op.drop_table('organization_role')
