"""Auto create profile on user creation

Revision ID: f1a2b3c4d5e6
Revises: e9f8a7b6c5d4
Create Date: 2025-09-30 11:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e9f8a7b6c5d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create trigger function to automatically create profile when user is created
    op.execute("""
        CREATE OR REPLACE FUNCTION create_user_profile()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Insert a new profile for the newly created user
            INSERT INTO profile (user_id, language_code, created_at, updated_at)
            VALUES (NEW.id, 'en', NOW(), NOW());
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger that fires after user insert
    op.execute("""
        CREATE TRIGGER trigger_create_user_profile
        AFTER INSERT ON "user"
        FOR EACH ROW
        EXECUTE FUNCTION create_user_profile();
    """)

    # Create profiles for any existing users that don't have one
    op.execute("""
        INSERT INTO profile (user_id, language_code, created_at, updated_at)
        SELECT id, 'en', NOW(), NOW()
        FROM "user"
        WHERE id NOT IN (SELECT user_id FROM profile);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop trigger
    op.execute('DROP TRIGGER IF EXISTS trigger_create_user_profile ON "user"')

    # Drop function
    op.execute('DROP FUNCTION IF EXISTS create_user_profile()')