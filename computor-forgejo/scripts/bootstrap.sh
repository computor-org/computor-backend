#!/bin/sh
set -e

echo "Creating admin user '${FORGEJO_ADMIN_USERNAME}' (ignored if already exists)..."
forgejo admin user create \
  --admin \
  --username "${FORGEJO_ADMIN_USERNAME}" \
  --password "${FORGEJO_ADMIN_PASSWORD}" \
  --email "${FORGEJO_ADMIN_EMAIL}" \
  --must-change-password=false 2>&1 || true

if [ -n "${FORGEJO_KEYCLOAK_CLIENT_ID}" ] && [ -n "${KEYCLOAK_URL}" ]; then
  echo "Configuring Keycloak OIDC source..."
  forgejo admin auth add-oauth \
    --name Keycloak \
    --provider openidConnect \
    --key "${FORGEJO_KEYCLOAK_CLIENT_ID}" \
    --secret "${FORGEJO_KEYCLOAK_CLIENT_SECRET}" \
    --auto-discover-url "${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/.well-known/openid-configuration" \
    --scopes "email profile" 2>&1 || true
fi

echo "Bootstrap complete."
