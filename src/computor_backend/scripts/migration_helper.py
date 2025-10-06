#!/usr/bin/env python3
"""
Helper script to generate and manage Alembic migrations for the database refactoring.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def run_command(cmd, cwd=None):
    """Run a shell command and return the output."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout

def main():
    # Set environment variables if not already set
    env_vars = {
        'POSTGRES_URL': os.environ.get('POSTGRES_URL', 'localhost'),
        'POSTGRES_USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'POSTGRES_PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        'POSTGRES_DB': os.environ.get('POSTGRES_DB', 'ctutor_test')
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Change to the directory containing alembic.ini
    alembic_dir = Path(__file__).parent
    os.chdir(alembic_dir)
    
    print("Database Refactoring Migration Helper")
    print("=====================================")
    print()
    print("1. Generate initial migration from SQLAlchemy models")
    print("2. Run migrations up to head")
    print("3. Show current migration status")
    print("4. Downgrade one migration")
    print("5. Create new migration")
    print()
    
    choice = input("Select an option (1-5): ").strip()
    
    if choice == '1':
        # Generate initial migration
        print("\nGenerating initial migration from SQLAlchemy models...")
        name = input("Enter migration name (e.g., 'initial_schema'): ").strip()
        run_command(f'alembic revision --autogenerate -m "{name}"')
        print("Migration generated successfully!")
        
    elif choice == '2':
        # Run migrations
        print("\nRunning migrations to head...")
        run_command('alembic upgrade head')
        print("Migrations completed successfully!")
        
    elif choice == '3':
        # Show status
        print("\nCurrent migration status:")
        run_command('alembic current')
        print("\nMigration history:")
        run_command('alembic history')
        
    elif choice == '4':
        # Downgrade
        print("\nDowngrading one migration...")
        run_command('alembic downgrade -1')
        print("Downgrade completed!")
        
    elif choice == '5':
        # Create new migration
        print("\nCreating new migration...")
        name = input("Enter migration name: ").strip()
        run_command(f'alembic revision --autogenerate -m "{name}"')
        print("Migration created successfully!")
        
    else:
        print("Invalid option selected.")

if __name__ == '__main__':
    main()