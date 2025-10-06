#!/usr/bin/env python3
"""
Script to create a completely fresh migration setup for the database refactoring.
This will generate a single comprehensive migration from the SQLAlchemy models.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a shell command and return the output."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout)
    return True

def main():
    # Set environment variables
    env_vars = {
        'POSTGRES_URL': 'localhost',
        'POSTGRES_USER': 'postgres',
        'POSTGRES_PASSWORD': 'postgres_secret',
        'POSTGRES_DB': 'codeability_fresh'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("Fresh Migration Setup for Database Refactoring")
    print("==============================================")
    
    # 1. Create a completely fresh database
    print("\n1. Creating fresh database...")
    if not run_command(f"PGPASSWORD={env_vars['POSTGRES_PASSWORD']} psql -h {env_vars['POSTGRES_URL']} -U {env_vars['POSTGRES_USER']} -c \"DROP DATABASE IF EXISTS {env_vars['POSTGRES_DB']};\""):
        print("Failed to drop database")
        return
    
    if not run_command(f"PGPASSWORD={env_vars['POSTGRES_PASSWORD']} psql -h {env_vars['POSTGRES_URL']} -U {env_vars['POSTGRES_USER']} -c \"CREATE DATABASE {env_vars['POSTGRES_DB']};\""):
        print("Failed to create database")
        return
    
    # 2. Clean up alembic versions directory
    print("\n2. Cleaning up migration files...")
    versions_dir = Path("alembic/versions")
    if versions_dir.exists():
        # Move old files to backup
        backup_dir = Path("alembic/old_versions_backup")
        backup_dir.mkdir(exist_ok=True)
        for file in versions_dir.glob("*.py"):
            if file.name != "__pycache__":
                shutil.move(str(file), str(backup_dir / file.name))
    
    # 3. Reset alembic state
    print("\n3. Resetting alembic state...")
    alembic_dir = Path("alembic")
    if (alembic_dir / "versions" / "alembic_version").exists():
        os.remove(alembic_dir / "versions" / "alembic_version")
    
    # 4. Create the extensions migration first
    print("\n4. Creating extensions migration...")
    extensions_content = '''"""Create PostgreSQL extensions and utility functions

Revision ID: 001_extensions
Revises: 
Create Date: 2025-07-11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_extensions'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS \\"uuid-ossp\\";")
    op.execute("CREATE EXTENSION IF NOT EXISTS ltree;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    
    # Create enums
    op.execute("""
        CREATE TYPE organization_type AS ENUM ('user', 'community', 'organization');
        CREATE TYPE user_type AS ENUM ('user', 'token');
        CREATE TYPE ctutor_group_type AS ENUM ('fixed', 'dynamic');
        CREATE TYPE ctutor_color AS ENUM (
            'red', 'orange', 'amber', 'yellow', 'lime', 'green', 'emerald', 
            'teal', 'cyan', 'sky', 'blue', 'indigo', 'violet', 'purple', 
            'fuchsia', 'pink', 'rose'
        );
    """)
    
    # Create utility functions
    op.execute("""
        CREATE OR REPLACE FUNCTION ctutor_valid_slug(value text) 
        RETURNS boolean 
        LANGUAGE plpgsql 
        AS $function$
        BEGIN
            RETURN value ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$';
        END;
        $function$;
    """)
    
    # Create sequences
    op.execute("CREATE SEQUENCE IF NOT EXISTS user_unique_fs_number_seq;")


def downgrade() -> None:
    # Drop sequences
    op.execute("DROP SEQUENCE IF EXISTS user_unique_fs_number_seq;")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS ctutor_valid_slug CASCADE;")
    
    # Drop types
    op.execute("DROP TYPE IF EXISTS ctutor_color CASCADE;")
    op.execute("DROP TYPE IF EXISTS ctutor_group_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS user_type CASCADE;")
    op.execute("DROP TYPE IF EXISTS organization_type CASCADE;")
    
    # Drop extensions
    op.execute("DROP EXTENSION IF EXISTS pgcrypto CASCADE;")
    op.execute("DROP EXTENSION IF EXISTS ltree CASCADE;")
    op.execute("DROP EXTENSION IF EXISTS \\"uuid-ossp\\" CASCADE;")
'''
    
    with open("alembic/versions/001_extensions.py", "w") as f:
        f.write(extensions_content)
    
    # 5. Apply extensions migration
    print("\n5. Applying extensions migration...")
    if not run_command("alembic upgrade 001_extensions"):
        print("Failed to apply extensions migration")
        return
    
    # 6. Generate schema migration from models
    print("\n6. Generating schema migration from SQLAlchemy models...")
    if not run_command("alembic revision --autogenerate -m 'initial_schema_from_sqlalchemy_models'"):
        print("Failed to generate schema migration")
        return
    
    # 7. Apply the schema migration
    print("\n7. Applying schema migration...")
    if not run_command("alembic upgrade head"):
        print("Failed to apply schema migration")
        return
    
    print("\n✅ Fresh migration setup completed successfully!")
    print(f"Database: {env_vars['POSTGRES_DB']}")
    print("Next steps:")
    print("1. Review the generated migration files")
    print("2. Test the migration on a copy of production data")
    print("3. Create a data seeder for fake data")

if __name__ == '__main__':
    main()