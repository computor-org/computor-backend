#!/bin/bash

# Start from home directory
cd /home/worker

# Run Alembic migrations
echo "Applying Alembic migrations..."
cd computor-backend/src/computor_backend && alembic upgrade head && cd /home/worker

# Restricted DB role for the coder temporal worker (no-op without
# CODER_WORKER_DB_PASSWORD). Non-fatal: only template rollouts depend on it.
(cd /home/worker/computor-backend/src \
    && python -m computor_backend.scripts.ensure_coder_worker_db_role) \
    || echo "WARNING: could not ensure the coder worker DB role"

# Start the server from the correct directory (stay in /home/worker)
cd /home/worker/computor-backend/src && python server.py
