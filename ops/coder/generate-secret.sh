#!/bin/bash
# Generate CODER_ADMIN_API_SECRET

SECRET=$(openssl rand -hex 32)
echo "CODER_ADMIN_API_SECRET=${SECRET}"
