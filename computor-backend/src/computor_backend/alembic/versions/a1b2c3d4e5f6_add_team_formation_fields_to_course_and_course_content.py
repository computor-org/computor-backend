"""add_team_formation_fields_to_course_and_course_content

Revision ID: a1b2c3d4e5f6
Revises: d6bf5cf6f474
Create Date: 2025-10-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd6bf5cf6f474'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add team formation configuration fields to course and course_content tables.

    Course fields provide defaults for all assignments in the course.
    CourseContent fields override course defaults for specific assignments.
    """

    # Add team formation fields to COURSE table (defaults for all assignments)
    op.add_column('course', sa.Column('team_mode', sa.String(50), nullable=True))
    op.add_column('course', sa.Column('team_min_group_size', sa.Integer(), nullable=True))
    op.add_column('course', sa.Column('team_allow_student_creation', sa.Boolean(), nullable=True))
    op.add_column('course', sa.Column('team_allow_join', sa.Boolean(), nullable=True))
    op.add_column('course', sa.Column('team_allow_leave', sa.Boolean(), nullable=True))
    op.add_column('course', sa.Column('team_auto_assign_unmatched', sa.Boolean(), nullable=True))
    op.add_column('course', sa.Column('team_lock_at_deadline', sa.Boolean(), nullable=True))
    op.add_column('course', sa.Column('team_require_approval', sa.Boolean(), nullable=True))

    # Add check constraint for team_mode enum
    op.create_check_constraint(
        'course_team_mode_check',
        'course',
        "team_mode IS NULL OR team_mode IN ('self_organized', 'instructor_predefined', 'hybrid')"
    )

    # Add check constraint for min_group_size
    op.create_check_constraint(
        'course_team_min_group_size_check',
        'course',
        'team_min_group_size IS NULL OR team_min_group_size >= 1'
    )

    # Add team formation fields to COURSE_CONTENT table (overrides for specific assignments)
    op.add_column('course_content', sa.Column('team_mode', sa.String(50), nullable=True))
    op.add_column('course_content', sa.Column('team_min_group_size', sa.Integer(), nullable=True))
    op.add_column('course_content', sa.Column('team_formation_deadline', sa.DateTime(timezone=True), nullable=True))
    op.add_column('course_content', sa.Column('team_allow_student_creation', sa.Boolean(), nullable=True))
    op.add_column('course_content', sa.Column('team_allow_join', sa.Boolean(), nullable=True))
    op.add_column('course_content', sa.Column('team_allow_leave', sa.Boolean(), nullable=True))
    op.add_column('course_content', sa.Column('team_auto_assign_unmatched', sa.Boolean(), nullable=True))
    op.add_column('course_content', sa.Column('team_lock_at_deadline', sa.Boolean(), nullable=True))
    op.add_column('course_content', sa.Column('team_require_approval', sa.Boolean(), nullable=True))

    # Add check constraint for team_mode enum
    op.create_check_constraint(
        'course_content_team_mode_check',
        'course_content',
        "team_mode IS NULL OR team_mode IN ('self_organized', 'instructor_predefined', 'hybrid')"
    )

    # Add check constraint for min_group_size
    op.create_check_constraint(
        'course_content_team_min_group_size_check',
        'course_content',
        'team_min_group_size IS NULL OR team_min_group_size >= 1'
    )

    # Add check constraint: team_min_group_size must be <= max_group_size
    op.create_check_constraint(
        'course_content_team_size_consistency_check',
        'course_content',
        'team_min_group_size IS NULL OR max_group_size IS NULL OR team_min_group_size <= max_group_size'
    )


def downgrade() -> None:
    """Remove team formation fields from course and course_content tables."""

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
