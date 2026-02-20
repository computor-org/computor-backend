#!/bin/bash

# Start from home directory
cd /home/uvicorn

# Run Alembic migrations
echo "Applying Alembic migrations..."
cd computor-backend/src/computor_backend && alembic upgrade head && cd /home/uvicorn

# Start the server from the correct directory (stay in /home/uvicorn)
cd /home/uvicorn/computor-backend/src && python server.py