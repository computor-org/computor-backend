"""Refactor submissions: rename CourseSubmissionGroup to SubmissionGroup, add artifact models

Revision ID: f5a6b7c8d9e0
Revises: e8b1f4c3d2a0
Create Date: 2024-09-28 19:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f5a6b7c8d9e0'
down_revision = 'e8b1f4c3d2a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new artifact tables

    # Create submission_artifact table
    op.create_table('submission_artifact',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('submission_group_id', postgresql.UUID(), nullable=False),
        sa.Column('uploaded_by_course_member_id', postgresql.UUID(), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('content_type', sa.String(length=120), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('bucket_name', sa.String(length=255), nullable=False),
        sa.Column('object_key', sa.String(length=2048), nullable=False),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create test_result table
    op.create_table('test_result',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submission_artifact_id', postgresql.UUID(), nullable=False),
        sa.Column('course_member_id', postgresql.UUID(), nullable=False),
        sa.Column('execution_backend_id', postgresql.UUID(), nullable=True),
        sa.Column('test_system_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(precision=53), server_default=sa.text('0.0'), nullable=False),
        sa.Column('max_score', sa.Float(precision=53), nullable=True),
        sa.Column('result_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('log_text', sa.String(), nullable=True),
        sa.Column('version_identifier', sa.String(length=2048), nullable=True),
        sa.Column('reference_version_identifier', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['course_member_id'], ['course_member.id'], ondelete='RESTRICT', onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['execution_backend_id'], ['execution_backend.id'], ondelete='RESTRICT', onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['submission_artifact_id'], ['submission_artifact.id'], ondelete='CASCADE', onupdate='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create result_artifact table
    op.create_table('result_artifact',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('test_result_id', postgresql.UUID(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=120), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('bucket_name', sa.String(length=255), nullable=False),
        sa.Column('object_key', sa.String(length=2048), nullable=False),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['test_result_id'], ['test_result.id'], ondelete='CASCADE', onupdate='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create artifact_grade table
    op.create_table('artifact_grade',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('graded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('artifact_id', postgresql.UUID(), nullable=False),
        sa.Column('graded_by_course_member_id', postgresql.UUID(), nullable=False),
        sa.Column('score', sa.Float(precision=53), nullable=False),
        sa.Column('max_score', sa.Float(precision=53), nullable=False),
        sa.Column('rubric', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('comment', sa.String(length=4096), nullable=True),
        sa.ForeignKeyConstraint(['artifact_id'], ['submission_artifact.id'], ondelete='CASCADE', onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['graded_by_course_member_id'], ['course_member.id'], ondelete='RESTRICT', onupdate='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create artifact_review table
    op.create_table('artifact_review',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('version', sa.BigInteger(), server_default=sa.text('0'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('artifact_id', postgresql.UUID(), nullable=False),
        sa.Column('reviewer_course_member_id', postgresql.UUID(), nullable=False),
        sa.Column('body', sa.String(length=4096), nullable=False),
        sa.Column('review_type', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['artifact_id'], ['submission_artifact.id'], ondelete='CASCADE', onupdate='RESTRICT'),
        sa.ForeignKeyConstraint(['reviewer_course_member_id'], ['course_member.id'], ondelete='RESTRICT', onupdate='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )

    # Rename course_submission_group to submission_group
    op.rename_table('course_submission_group', 'submission_group')
    op.rename_table('course_submission_group_member', 'submission_group_member')

    # Update foreign key column names in submission_group_member table
    op.alter_column('submission_group_member',
                    'course_submission_group_id',
                    new_column_name='submission_group_id')

    # Update foreign key column names in result table
    op.alter_column('result',
                    'course_submission_group_id',
                    new_column_name='submission_group_id')

    # Update foreign key constraints (drop old, add new)
    op.drop_constraint('submission_group_member_course_submission_group_id_fkey', 'submission_group_member', type_='foreignkey')
    op.create_foreign_key('submission_group_member_submission_group_id_fkey',
                         'submission_group_member', 'submission_group',
                         ['submission_group_id'], ['id'],
                         ondelete='CASCADE', onupdate='RESTRICT')

    op.drop_constraint('result_course_submission_group_id_fkey', 'result', type_='foreignkey')
    op.create_foreign_key('result_submission_group_id_fkey',
                         'result', 'submission_group',
                         ['submission_group_id'], ['id'],
                         ondelete='SET NULL', onupdate='RESTRICT')

    # Update indexes
    op.drop_index('course_submission_group_member_key', 'submission_group_member')
    op.create_index('submission_group_member_key', 'submission_group_member',
                    ['submission_group_id', 'course_member_id'], unique=True)

    op.drop_index('result_version_identifier_group_content_partial_key', 'result')
    op.create_index('result_version_identifier_group_content_partial_key', 'result',
                    ['submission_group_id', 'version_identifier', 'course_content_id'],
                    unique=True, postgresql_where=sa.text('status NOT IN (1, 2, 6)'))

    # Add foreign key constraint for submission_artifact after renaming
    op.create_foreign_key('submission_artifact_submission_group_id_fkey',
                         'submission_artifact', 'submission_group',
                         ['submission_group_id'], ['id'],
                         ondelete='CASCADE', onupdate='RESTRICT')

    op.create_foreign_key('submission_artifact_uploaded_by_course_member_id_fkey',
                         'submission_artifact', 'course_member',
                         ['uploaded_by_course_member_id'], ['id'],
                         ondelete='SET NULL', onupdate='RESTRICT')

    # Create indexes for new tables
    op.create_index('submission_artifact_submission_group_idx', 'submission_artifact', ['submission_group_id'])
    op.create_index('submission_artifact_uploaded_by_idx', 'submission_artifact', ['uploaded_by_course_member_id'])
    op.create_index('submission_artifact_uploaded_at_idx', 'submission_artifact', ['uploaded_at'])

    op.create_index('test_result_submission_artifact_idx', 'test_result', ['submission_artifact_id'])
    op.create_index('test_result_course_member_idx', 'test_result', ['course_member_id'])
    op.create_index('test_result_created_at_idx', 'test_result', ['created_at'])
    op.create_index('test_result_unique_success', 'test_result',
                    ['submission_artifact_id', 'course_member_id'],
                    unique=True, postgresql_where=sa.text('status NOT IN (1, 2, 6)'))

    op.create_index('result_artifact_test_result_idx', 'result_artifact', ['test_result_id'])
    op.create_index('result_artifact_created_at_idx', 'result_artifact', ['created_at'])

    op.create_index('artifact_grade_artifact_idx', 'artifact_grade', ['artifact_id'])
    op.create_index('artifact_grade_grader_idx', 'artifact_grade', ['graded_by_course_member_id'])
    op.create_index('artifact_grade_graded_at_idx', 'artifact_grade', ['graded_at'])

    op.create_index('artifact_review_artifact_idx', 'artifact_review', ['artifact_id'])
    op.create_index('artifact_review_reviewer_idx', 'artifact_review', ['reviewer_course_member_id'])
    op.create_index('artifact_review_created_at_idx', 'artifact_review', ['created_at'])


def downgrade() -> None:
    # Drop indexes for new tables
    op.drop_index('artifact_review_created_at_idx', 'artifact_review')
    op.drop_index('artifact_review_reviewer_idx', 'artifact_review')
    op.drop_index('artifact_review_artifact_idx', 'artifact_review')

    op.drop_index('artifact_grade_graded_at_idx', 'artifact_grade')
    op.drop_index('artifact_grade_grader_idx', 'artifact_grade')
    op.drop_index('artifact_grade_artifact_idx', 'artifact_grade')

    op.drop_index('result_artifact_created_at_idx', 'result_artifact')
    op.drop_index('result_artifact_test_result_idx', 'result_artifact')

    op.drop_index('test_result_unique_success', 'test_result')
    op.drop_index('test_result_created_at_idx', 'test_result')
    op.drop_index('test_result_course_member_idx', 'test_result')
    op.drop_index('test_result_submission_artifact_idx', 'test_result')

    op.drop_index('submission_artifact_uploaded_at_idx', 'submission_artifact')
    op.drop_index('submission_artifact_uploaded_by_idx', 'submission_artifact')
    op.drop_index('submission_artifact_submission_group_idx', 'submission_artifact')

    # Drop new tables
    op.drop_table('artifact_review')
    op.drop_table('artifact_grade')
    op.drop_table('result_artifact')
    op.drop_table('test_result')
    op.drop_table('submission_artifact')

    # Rename back the column names
    op.alter_column('result',
                    'submission_group_id',
                    new_column_name='course_submission_group_id')

    op.alter_column('submission_group_member',
                    'submission_group_id',
                    new_column_name='course_submission_group_id')

    # Restore foreign key constraints with old names
    op.drop_constraint('result_submission_group_id_fkey', 'result', type_='foreignkey')
    op.create_foreign_key('result_course_submission_group_id_fkey',
                         'result', 'submission_group',
                         ['course_submission_group_id'], ['id'],
                         ondelete='SET NULL', onupdate='RESTRICT')

    op.drop_constraint('submission_group_member_submission_group_id_fkey', 'submission_group_member', type_='foreignkey')
    op.create_foreign_key('submission_group_member_course_submission_group_id_fkey',
                         'submission_group_member', 'submission_group',
                         ['course_submission_group_id'], ['id'],
                         ondelete='CASCADE', onupdate='RESTRICT')

    # Restore indexes with old names
    op.drop_index('submission_group_member_key', 'submission_group_member')
    op.create_index('course_submission_group_member_key', 'submission_group_member',
                    ['course_submission_group_id', 'course_member_id'], unique=True)

    op.drop_index('result_version_identifier_group_content_partial_key', 'result')
    op.create_index('result_version_identifier_group_content_partial_key', 'result',
                    ['course_submission_group_id', 'version_identifier', 'course_content_id'],
                    unique=True, postgresql_where=sa.text('status NOT IN (1, 2, 6)'))

    # Rename tables back
    op.rename_table('submission_group_member', 'course_submission_group_member')
    op.rename_table('submission_group', 'course_submission_group')