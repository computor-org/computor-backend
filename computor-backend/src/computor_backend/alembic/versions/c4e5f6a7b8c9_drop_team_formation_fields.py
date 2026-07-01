"""drop team formation fields from course and course_content

Removes the unused team-formation configuration columns (and their check
constraints) that were added by a1b2c3d4e5f6. These columns were never read by
any application code — team/group sizing is driven by
``course_content.max_group_size`` -> ``submission_group.max_group_size``, and the
half-built team-formation feature (endpoints, service, DTOs) has been removed.

This is the inverse of a1b2c3d4e5f6: ``upgrade()`` here mirrors that migration's
``downgrade()``, and ``downgrade()`` here mirrors its ``upgrade()``.

Revision ID: c4e5f6a7b8c9
Revises: b3d4e5f6a7b8
Create Date: 2026-07-01 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e5f6a7b8c9'
down_revision: Union[str, None] = 'b3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop team formation fields from course and course_content tables."""

    # Drop constraints first
    op.drop_constraint('course_content_team_size_consistency_check', 'course_content', type_='check')
    op.drop_constraint('course_content_team_min_group_size_check', 'course_content', type_='check')
    op.drop_constraint('course_content_team_mode_check', 'course_content', type_='check')
    op.drop_constraint('course_team_min_group_size_check', 'course', type_='check')
    op.drop_constraint('course_team_mode_check', 'course', type_='check')

    # Drop course_content columns
    op.drop_column('course_content', 'team_require_approval')
    op.drop_column('course_content', 'team_lock_at_deadline')
    op.drop_column('course_content', 'team_auto_assign_unmatched')
    op.drop_column('course_content', 'team_allow_leave')
    op.drop_column('course_content', 'team_allow_join')
    op.drop_column('course_content', 'team_allow_student_creation')
    op.drop_column('course_content', 'team_formation_deadline')
    op.drop_column('course_content', 'team_min_group_size')
    op.drop_column('course_content', 'team_mode')

    # Drop course columns
    op.drop_column('course', 'team_require_approval')
    op.drop_column('course', 'team_lock_at_deadline')
    op.drop_column('course', 'team_auto_assign_unmatched')
    op.drop_column('course', 'team_allow_leave')
    op.drop_column('course', 'team_allow_join')
    op.drop_column('course', 'team_allow_student_creation')
    op.drop_column('course', 'team_min_group_size')
    op.drop_column('course', 'team_mode')


def downgrade() -> None:
    """Re-add team formation fields to course and course_content tables."""

    # Re-add team formation fields to COURSE table (defaults for all assignments)
    op.add_column('course', sa.Column('team_mode', sa.String(50), nullable=True))
    op.add_column('course', sa.Column('team_min_group_size', sa.Integer(), nullable=True))
    op.add_column('course', sa.Column('team_allow_student_creation', sa.Boolean(), nullable=True))
    op.add_column('course', sa.Column('team_allow_join', sa.Boolean(), nullable=True))
    op.add_column('course', sa.Column('team_allow_leave', sa.Boolean(), nullable=True))
    op.add_column('course', sa.Column('team_auto_assign_unmatched', sa.Boolean(), nullable=True))
    op.add_column('course', sa.Column('team_lock_at_deadline', sa.Boolean(), nullable=True))
    op.add_column('course', sa.Column('team_require_approval', sa.Boolean(), nullable=True))

    op.create_check_constraint(
        'course_team_mode_check',
        'course',
        "team_mode IS NULL OR team_mode IN ('self_organized', 'instructor_predefined', 'hybrid')"
    )
    op.create_check_constraint(
        'course_team_min_group_size_check',
        'course',
        'team_min_group_size IS NULL OR team_min_group_size >= 1'
    )

    # Re-add team formation fields to COURSE_CONTENT table (per-assignment overrides)
    op.add_column('course_content', sa.Column('team_mode', sa.String(50), nullable=True))
    op.add_column('course_content', sa.Column('team_min_group_size', sa.Integer(), nullable=True))
    op.add_column('course_content', sa.Column('team_formation_deadline', sa.DateTime(timezone=True), nullable=True))
    op.add_column('course_content', sa.Column('team_allow_student_creation', sa.Boolean(), nullable=True))
    op.add_column('course_content', sa.Column('team_allow_join', sa.Boolean(), nullable=True))
    op.add_column('course_content', sa.Column('team_allow_leave', sa.Boolean(), nullable=True))
    op.add_column('course_content', sa.Column('team_auto_assign_unmatched', sa.Boolean(), nullable=True))
    op.add_column('course_content', sa.Column('team_lock_at_deadline', sa.Boolean(), nullable=True))
    op.add_column('course_content', sa.Column('team_require_approval', sa.Boolean(), nullable=True))

    op.create_check_constraint(
        'course_content_team_mode_check',
        'course_content',
        "team_mode IS NULL OR team_mode IN ('self_organized', 'instructor_predefined', 'hybrid')"
    )
    op.create_check_constraint(
        'course_content_team_min_group_size_check',
        'course_content',
        'team_min_group_size IS NULL OR team_min_group_size >= 1'
    )
    op.create_check_constraint(
        'course_content_team_size_consistency_check',
        'course_content',
        'team_min_group_size IS NULL OR max_group_size IS NULL OR team_min_group_size <= max_group_size'
    )
