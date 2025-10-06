#!/bin/bash

set -a
source .env
set +a

echo "Initializing system data..."
cd src/computor_backend && python scripts/initialize_system_data.py