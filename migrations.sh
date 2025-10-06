#!/bin/bash

set -a
source .env
set +a

echo "Applying Alembic migrations..."
cd src
export PYTHONPATH=$PWD:$PYTHONPATH
cd computor_backend && alembic upgrade head