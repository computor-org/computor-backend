"""add_audit_triggers_for_created_by_updated_by

Revision ID: d6bf5cf6f474
Revises: f1a2b3c4d5e6
Create Date: 2025-10-07 16:13:32.496670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6bf5cf6f474'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add audit triggers for created_by/updated_by."""

    # Create trigger function to automatically set created_by and updated_by
    # from the PostgreSQL app.user_id session variable
    op.execute("""
        CREATE OR REPLACE FUNCTION set_audit_fields()
        RETURNS TRIGGER AS $$
        DECLARE
            user_id_value UUID;
        BEGIN
            -- Try to get the user_id from the session variable
            -- Use COALESCE with NULL to handle cases where the variable is not set
            BEGIN
                user_id_value := current_setting('app.user_id', true)::UUID;
            EXCEPTION
                WHEN OTHERS THEN
                    user_id_value := NULL;
            END;

            -- On INSERT: set created_by if user_id is available and created_by is not already set
            IF (TG_OP = 'INSERT') THEN
                IF user_id_value IS NOT NULL AND NEW.created_by IS NULL THEN
                    NEW.created_by := user_id_value;
                END IF;
                IF user_id_value IS NOT NULL AND NEW.updated_by IS NULL THEN
                    NEW.updated_by := user_id_value;
                END IF;
            END IF;

            -- On UPDATE: always update updated_by if user_id is available
            IF (TG_OP = 'UPDATE') THEN
                IF user_id_value IS NOT NULL THEN
                    NEW.updated_by := user_id_value;
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # List of all tables that have BOTH created_by AND updated_by columns
    # Generated from model analysis - only tables with both columns
    tables_with_audit = [
        'account',
        'course',
        'course_content',
        'course_content_deployment',
        'course_content_type',
        'course_execution_backend',
        'course_family',
        'course_group',
        'course_member',
        'course_member_comment',
        'example',
        'example_repository',
        'execution_backend',
        'group',
        'group_claim',
        'message',
        'message_read',
        'organization',
        'profile',
        'result',
        'role_claim',
        'session',
        'student_profile',
        'submission_group',
        'submission_group_member',
        'user',
        'user_group',
        'user_role',
    ]

    # Create triggers for each table
    # Note: Quote table names to handle reserved keywords like "user" and "group"
    for table in tables_with_audit:
        op.execute(f"""
            CREATE TRIGGER {table}_audit_trigger
            BEFORE INSERT OR UPDATE ON "{table}"
            FOR EACH ROW
            EXECUTE FUNCTION set_audit_fields();
        """)


def downgrade() -> None:
    """Downgrade schema - remove audit triggers."""

    # List of all tables that have audit triggers (must match upgrade)
    tables_with_audit = [
        'account',
        'course',
        'course_content',
        'course_content_deployment',
        'course_content_type',
        'course_execution_backend',
        'course_family',
        'course_group',
        'course_member',
        'course_member_comment',
        'example',
        'example_repository',
        'execution_backend',
        'group',
        'group_claim',
        'message',
        'message_read',
        'organization',
        'profile',
        'result',
        'role_claim',
        'session',
        'student_profile',
        'submission_group',
        'submission_group_member',
        'user',
        'user_group',
        'user_role',
    ]

    # Drop triggers
    # Note: Quote table names to handle reserved keywords like "user" and "group"
    for table in tables_with_audit:
        op.execute(f"""
            DROP TRIGGER IF EXISTS {table}_audit_trigger ON "{table}";
        """)

    # Drop trigger function
    op.execute("""
        DROP FUNCTION IF EXISTS set_audit_fields();
    """)
