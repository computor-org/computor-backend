#!/bin/bash

set -a
source .env
set +a

cd computor-backend/src && python3 server.py