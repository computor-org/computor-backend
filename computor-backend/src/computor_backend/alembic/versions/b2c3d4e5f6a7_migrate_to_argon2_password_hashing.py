"""Migrate to Argon2 password hashing

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-10-24 00:00:00.000000

Changes:
- Increase password column length from 255 to 512 chars for Argon2 hashes
- Add password_reset_required boolean flag for tracking reset status
- Invalidate all existing encrypted passwords (set to NULL)
- Mark all existing users as requiring password reset

Security Impact:
This migration improves password security by replacing reversible encryption
with industry-standard Argon2id one-way hashing. All existing passwords will
be invalidated, requiring users to reset their passwords.

Deployment Notes:
1. After running this migration, run initialize_system_data.py to reset admin password
2. Communicate to all users that passwords have been reset
3. Provide password reset mechanism via admin or self-service
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade to Argon2 password hashing.

    Steps:
    1. Add password_reset_required column
    2. Increase password column length for Argon2 hashes
    3. Invalidate all existing encrypted passwords
    4. Mark all users as requiring password reset
    """

    # Step 1: Add password_reset_required column
    # This tracks which users need to set a new password
    op.add_column(
        'user',
        sa.Column(
            'password_reset_required',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false')
        )
    )

    # Step 2: Increase password column length
    # Argon2 hashes are ~100 chars but we use 512 for safety
    # Old encrypted passwords were ~255 chars
    op.alter_column(
        'user',
        'password',
        type_=sa.String(512),
        existing_type=sa.String(255),
        nullable=True,  # Keep nullable for SSO users who have no password
    )

    # Step 3: Invalidate all existing encrypted passwords
    # We cannot convert encrypted passwords to Argon2 hashes
    # because we need the plaintext password to hash it
    # Setting to NULL forces password reset
    op.execute(
        """
        UPDATE "user"
        SET password = NULL
        WHERE password IS NOT NULL
        AND user_type = 'user'
        """
    )

    # Step 4: Mark all users with passwords as needing reset
    # This includes any user who had a password (now NULL)
    # SSO users (password was already NULL) are not affected
    op.execute(
        """
        UPDATE "user"
        SET password_reset_required = true
        WHERE user_type = 'user'
        """
    )

    # Note: Token users are not affected as they use token_expiration


def downgrade() -> None:
    """
    Downgrade from Argon2 to old system.

    Warning: This is a destructive operation. All Argon2 hashes
    will be lost as they cannot be converted back to encrypted passwords.
    """

    # Remove password_reset_required column
    op.drop_column('user', 'password_reset_required')

    # Restore original password column type
    # Note: All existing password data will be lost/truncated
    op.alter_column(
        'user',
        'password',
        type_=sa.String(255),
        existing_type=sa.String(512),
        nullable=True,
    )

    # Clear all passwords as they cannot be converted back
    op.execute(
        """
        UPDATE "user"
        SET password = NULL
        WHERE password IS NOT NULL
        """
    )
