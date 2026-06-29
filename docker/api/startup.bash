#!/bin/bash

# Start from home directory
cd /home/worker

# Run Alembic migrations
echo "Applying Alembic migrations..."
cd computor-backend/src/computor_backend && alembic upgrade head && cd /home/worker

# Start the server from the correct directory (stay in /home/worker)
cd /home/worker/computor-backend/src && python server.py
