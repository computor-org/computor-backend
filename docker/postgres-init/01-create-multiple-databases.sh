#!/bin/bash
set -e

# This script creates multiple databases in PostgreSQL
# It's only executed on first container initialization

# Function to create a database if it doesn't exist
create_database() {
    local database=$1
    echo "Creating database: $database"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        SELECT 'CREATE DATABASE $database'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
EOSQL
    echo "Database $database ready."
}

# Parse POSTGRES_MULTIPLE_DATABASES variable (comma-separated)
if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
    echo "Multiple databases requested: $POSTGRES_MULTIPLE_DATABASES"

    # Convert comma-separated string to array
    IFS=',' read -ra DATABASES <<< "$POSTGRES_MULTIPLE_DATABASES"

    # Create each database
    for db in "${DATABASES[@]}"; do
        # Trim whitespace
        db=$(echo "$db" | xargs)
        if [ -n "$db" ] && [ "$db" != "$POSTGRES_DB" ]; then
            create_database "$db"
        fi
    done
fi

echo "Database initialization complete."