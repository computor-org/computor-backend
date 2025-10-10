#!/bin/bash

# Start from home directory
cd /home/uvicorn

# Run Alembic migrations
echo "Applying Alembic migrations..."
cd computor-backend/src/computor_backend && alembic upgrade head && cd /home/uvicorn

echo "Initializing system data..."
cd computor-backend/src/computor_backend && python scripts/initialize_system_data.py && cd /home/uvicorn

# Start the server from the correct directory
python computor-backend/src/server.py