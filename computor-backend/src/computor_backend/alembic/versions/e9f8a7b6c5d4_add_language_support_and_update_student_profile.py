"""Add language support and update student_profile organization

Revision ID: e9f8a7b6c5d4
Revises: db5ca83fadfc
Create Date: 2025-09-30 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9f8a7b6c5d4'
down_revision: Union[str, None] = 'db5ca83fadfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create language table
    op.create_table(
        'language',
        sa.Column('code', sa.String(length=2), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('native_name', sa.String(length=255), nullable=True),
        sa.CheckConstraint("length(code) = 2", name='ck_language_code_length'),
        sa.CheckConstraint("code ~ '^[a-z]{2}$'", name='ck_language_code_format'),
        sa.PrimaryKeyConstraint('code')
    )

    # Insert standard languages (ISO 639-1 codes)
    op.execute("""
        INSERT INTO language (code, name, native_name) VALUES
        ('en', 'English', 'English'),
        ('de', 'German', 'Deutsch'),
        ('es', 'Spanish', 'Español'),
        ('fr', 'French', 'Français'),
        ('it', 'Italian', 'Italiano'),
        ('pt', 'Portuguese', 'Português'),
        ('nl', 'Dutch', 'Nederlands'),
        ('pl', 'Polish', 'Polski'),
        ('ru', 'Russian', 'Русский'),
        ('ja', 'Japanese', '日本語'),
        ('zh', 'Chinese', '中文'),
        ('ko', 'Korean', '한국어'),
        ('ar', 'Arabic', 'العربية'),
        ('hi', 'Hindi', 'हिन्दी'),
        ('tr', 'Turkish', 'Türkçe'),
        ('sv', 'Swedish', 'Svenska'),
        ('da', 'Danish', 'Dansk'),
        ('no', 'Norwegian', 'Norsk'),
        ('fi', 'Finnish', 'Suomi'),
        ('cs', 'Czech', 'Čeština'),
        ('hu', 'Hungarian', 'Magyar'),
        ('ro', 'Romanian', 'Română'),
        ('el', 'Greek', 'Ελληνικά'),
        ('uk', 'Ukrainian', 'Українська')
        ON CONFLICT (code) DO NOTHING
    """)

    # Add language_code to profile table
    op.add_column('profile', sa.Column('language_code', sa.String(length=2), nullable=True))
    op.create_foreign_key(
        'fk_profile_language_code',
        'profile',
        'language',
        ['language_code'],
        ['code'],
        ondelete='SET NULL',
        onupdate='CASCADE'
    )

    # Add language_code to course table
    op.add_column('course', sa.Column('language_code', sa.String(length=2), nullable=True))
    op.create_foreign_key(
        'fk_course_language_code',
        'course',
        'language',
        ['language_code'],
        ['code'],
        ondelete='SET NULL',
        onupdate='CASCADE'
    )

    # Add organization_id to student_profile table
    op.add_column('student_profile', sa.Column('organization_id', sa.dialects.postgresql.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_student_profile_organization_id',
        'student_profile',
        'organization',
        ['organization_id'],
        ['id'],
        ondelete='CASCADE',
        onupdate='RESTRICT'
    )

    # Make organization_id NOT NULL after adding it
    # (assuming existing records will be handled separately or there are none)
    op.alter_column('student_profile', 'organization_id', nullable=False)

    # Create trigger function to set default language to 'en' for courses
    op.execute("""
        CREATE OR REPLACE FUNCTION set_default_course_language()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.language_code IS NULL THEN
                NEW.language_code := 'en';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trigger_set_default_course_language
        BEFORE INSERT ON course
        FOR EACH ROW
        EXECUTE FUNCTION set_default_course_language();
    """)

    # Create trigger function to set default language to 'en' for profiles
    op.execute("""
        CREATE OR REPLACE FUNCTION set_default_profile_language()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.language_code IS NULL THEN
                NEW.language_code := 'en';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trigger_set_default_profile_language
        BEFORE INSERT ON profile
        FOR EACH ROW
        EXECUTE FUNCTION set_default_profile_language();
    """)

    # Update existing courses to have 'en' as default language
    op.execute("UPDATE course SET language_code = 'en' WHERE language_code IS NULL")

    # Update existing profiles to have 'en' as default language
    op.execute("UPDATE profile SET language_code = 'en' WHERE language_code IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_set_default_profile_language ON profile")
    op.execute("DROP FUNCTION IF EXISTS set_default_profile_language()")

    op.execute("DROP TRIGGER IF EXISTS trigger_set_default_course_language ON course")
    op.execute("DROP FUNCTION IF EXISTS set_default_course_language()")

    # Remove organization_id from student_profile
    op.drop_constraint('fk_student_profile_organization_id', 'student_profile', type_='foreignkey')
    op.drop_column('student_profile', 'organization_id')

    # Remove language_code from course
    op.drop_constraint('fk_course_language_code', 'course', type_='foreignkey')
    op.drop_column('course', 'language_code')

    # Remove language_code from profile
    op.drop_constraint('fk_profile_language_code', 'profile', type_='foreignkey')
    op.drop_column('profile', 'language_code')

    # Drop language table
    op.drop_table('language')