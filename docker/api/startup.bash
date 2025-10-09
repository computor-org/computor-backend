#!/bin/bash

# Run Alembic migrations
echo "Applying Alembic migrations..."
cd computor-backend/src/computor_backend && alembic upgrade head

echo "Initializing system data..."
python scripts/initialize_system_data.py

# Go back to home directory before starting server
cd /home/uvicorn

# Start the server from the correct directory
python computor-backend/src/server.py