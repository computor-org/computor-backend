#!/bin/sh
set -e

echo "Creating admin user '${FORGEJO_ADMIN_USERNAME}' (ignored if already exists)..."
forgejo admin user create \
  --admin \
  --username "${FORGEJO_ADMIN_USERNAME}" \
  --password "${FORGEJO_ADMIN_PASSWORD}" \
  --email "${FORGEJO_ADMIN_EMAIL}" \
  --must-change-password=false 2>&1 || true

# Keycloak OIDC setup is handled separately by keycloak_setup.sh (the
# forgejo-keycloak overlay), which runs only when Keycloak is enabled.

echo "Bootstrap complete."
