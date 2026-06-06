#!/bin/sh
set -e

# Register Keycloak as an OIDC login source inside Forgejo.
#
# The Keycloak side is fully declarative: the 'forgejo' client (its fixed secret,
# scopes and redirect URIs) is defined in the realm import
# (data/keycloak/computor-realm.json) and the backend reconciles the public
# redirect URI on startup. This script only does the one piece that cannot be
# declared ahead of time — a Forgejo login source is a DB row with no config-file
# equivalent, so it must be created via the admin CLI at runtime.
#
# Idempotent: updates the existing source in place on every boot, so a rotated
# secret or changed discovery URL self-heals with nothing to do manually.

CLIENT_ID="forgejo"
SECRET="${FORGEJO_KEYCLOAK_CLIENT_SECRET:?FORGEJO_KEYCLOAK_CLIENT_SECRET is required}"
DISCOVER_URL="${KEYCLOAK_INTERNAL_URL}/realms/${KEYCLOAK_REALM}/.well-known/openid-configuration"

echo "=== Forgejo Keycloak OIDC source ==="
echo "Discover: ${DISCOVER_URL}"

# `forgejo admin auth list` prints: "ID  Name  Type  Enabled" (header first).
# Match the data row whose Name column is exactly "Keycloak".
EXISTING_ID=$(forgejo admin auth list 2>/dev/null | awk '$2 == "Keycloak" { print $1; exit }')

if [ -n "${EXISTING_ID}" ]; then
  echo "Updating existing source (id=${EXISTING_ID})..."
  forgejo admin auth update-oauth \
    --id "${EXISTING_ID}" \
    --name Keycloak \
    --provider openidConnect \
    --key "${CLIENT_ID}" \
    --secret "${SECRET}" \
    --auto-discover-url "${DISCOVER_URL}" \
    --scopes "email profile"
else
  echo "Adding source 'Keycloak'..."
  forgejo admin auth add-oauth \
    --name Keycloak \
    --provider openidConnect \
    --key "${CLIENT_ID}" \
    --secret "${SECRET}" \
    --auto-discover-url "${DISCOVER_URL}" \
    --scopes "email profile"
fi

echo "=== Done ==="
