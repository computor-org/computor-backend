#!/bin/bash

set -a
source .env
set +a

echo "Applying Alembic migrations..."
cd computor-backend/src
export PYTHONPATH=$PWD:$PYTHONPATH
cd computor_backend && alembic upgrade head
cd .. && python -m computor_backend.scripts.ensure_coder_worker_db_role