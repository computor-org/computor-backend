"""fix_email_uniqueness_constraints

Revision ID: 4327038d4ae3
Revises: a5d4bb78da7a
Create Date: 2025-11-09 13:21:07.962009

This migration fixes email uniqueness constraints to enforce:
1. User can have multiple student_profiles (one per organization) with same email
2. Emails cannot be shared across different users (globally unique per user)
3. User.email remains globally unique
4. StudentProfile.student_email can repeat for same user_id but not across users

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4327038d4ae3'
down_revision: Union[str, None] = 'a5d4bb78da7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Step 1: Drop existing unique constraints on student_profile
    op.drop_constraint('student_profile_user_id_key', 'student_profile', type_='unique')
    op.drop_constraint('student_profile_student_email_key', 'student_profile', type_='unique')

    # Step 2: Add composite unique constraint (user_id, organization_id)
    # This ensures one profile per user per organization
    op.create_unique_constraint(
        'uq_student_profile_user_org',
        'student_profile',
        ['user_id', 'organization_id']
    )

    # Step 3: Create function to check email uniqueness across users
    # This function ensures that an email can only belong to ONE user across ALL tables
    op.execute("""
        CREATE OR REPLACE FUNCTION check_email_uniqueness_across_users()
        RETURNS TRIGGER AS $$
        DECLARE
            other_user_id UUID;
            email_to_check TEXT;
        BEGIN
            -- Determine which table triggered and get the email to check
            IF TG_TABLE_NAME = 'user' THEN
                email_to_check := NEW.email;

                -- Check if this email exists in student_profile for a DIFFERENT user
                SELECT DISTINCT user_id INTO other_user_id
                FROM student_profile
                WHERE LOWER(student_email) = LOWER(email_to_check)
                  AND user_id != NEW.id
                LIMIT 1;

                IF other_user_id IS NOT NULL THEN
                    RAISE EXCEPTION 'Email "%" is already used by another user in student_profile table', email_to_check
                        USING ERRCODE = 'unique_violation',
                              HINT = 'Each email must be unique across all users';
                END IF;

            ELSIF TG_TABLE_NAME = 'student_profile' THEN
                email_to_check := NEW.student_email;

                -- Check if this email exists in user table for a DIFFERENT user
                SELECT id INTO other_user_id
                FROM "user"
                WHERE LOWER(email) = LOWER(email_to_check)
                  AND id != NEW.user_id
                LIMIT 1;

                IF other_user_id IS NOT NULL THEN
                    RAISE EXCEPTION 'Email "%" is already used by another user in user table', email_to_check
                        USING ERRCODE = 'unique_violation',
                              HINT = 'Each email must be unique across all users';
                END IF;

                -- Check if this email exists in student_profile for a DIFFERENT user
                SELECT DISTINCT user_id INTO other_user_id
                FROM student_profile
                WHERE LOWER(student_email) = LOWER(email_to_check)
                  AND user_id != NEW.user_id
                  AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::UUID)  -- Exclude self on UPDATE
                LIMIT 1;

                IF other_user_id IS NOT NULL THEN
                    RAISE EXCEPTION 'Email "%" is already used by another user in student_profile table', email_to_check
                        USING ERRCODE = 'unique_violation',
                              HINT = 'Each email must be unique across all users';
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Step 4: Create triggers on both tables
    op.execute("""
        CREATE TRIGGER trigger_check_email_uniqueness_user
        BEFORE INSERT OR UPDATE OF email ON "user"
        FOR EACH ROW
        WHEN (NEW.email IS NOT NULL)
        EXECUTE FUNCTION check_email_uniqueness_across_users();
    """)

    op.execute("""
        CREATE TRIGGER trigger_check_email_uniqueness_student_profile
        BEFORE INSERT OR UPDATE OF student_email ON student_profile
        FOR EACH ROW
        WHEN (NEW.student_email IS NOT NULL)
        EXECUTE FUNCTION check_email_uniqueness_across_users();
    """)


def downgrade() -> None:
    """Downgrade schema."""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_check_email_uniqueness_student_profile ON student_profile")
    op.execute("DROP TRIGGER IF EXISTS trigger_check_email_uniqueness_user ON \"user\"")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS check_email_uniqueness_across_users()")

    # Drop composite unique constraint
    op.drop_constraint('uq_student_profile_user_org', 'student_profile', type_='unique')

    # Restore original unique constraints
    op.create_unique_constraint('student_profile_student_email_key', 'student_profile', ['student_email'])
    op.create_unique_constraint('student_profile_user_id_key', 'student_profile', ['user_id'])
