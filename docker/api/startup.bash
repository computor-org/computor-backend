#!/bin/bash


# Run Alembic migrations
echo "Applying Alembic migrations..."
cd src/computor_backend && alembic upgrade head
#export PYTHONPATH=$PWD:$PYTHONPATH

echo "Initializing system data..."
python scripts/initialize_system_data.py

cd ..
# Start the server
python server.py