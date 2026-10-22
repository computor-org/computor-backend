"""Profile language stays unset until the user chooses one

Every profile was created with ``language_code = 'en'``: the user-creation
trigger from f1a2b3c4d5e6 inserted it, and the profile trigger from
e9f8a7b6c5d4 replaced NULL with it. Clients read the profile language as the
learner's explicit choice and only fall back to the course language when it is
unset, so learners in German courses were shown English instructions.

New profiles now start without a language, NULL stays NULL, and existing
'en' values are cleared. A stored 'en' cannot be told apart from the forced
default, so a learner who wants English regardless of the course chooses it
again in the profile. Other languages were explicit choices and are kept.

Revision ID: b7d2e4f6a8c1
Revises: 9c1e7a3b5d20
"""
from alembic import op


revision = 'b7d2e4f6a8c1'
down_revision = '9c1e7a3b5d20'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION create_user_profile()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO profile (user_id, created_at, updated_at)
            VALUES (NEW.id, NOW(), NOW());
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute('DROP TRIGGER IF EXISTS trigger_set_default_profile_language ON profile')
    op.execute('DROP FUNCTION IF EXISTS set_default_profile_language()')
    op.execute("UPDATE profile SET language_code = NULL WHERE language_code = 'en'")


def downgrade() -> None:
    op.execute("UPDATE profile SET language_code = 'en' WHERE language_code IS NULL")
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
    op.execute("""
        CREATE OR REPLACE FUNCTION create_user_profile()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO profile (user_id, language_code, created_at, updated_at)
            VALUES (NEW.id, 'en', NOW(), NOW());
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
