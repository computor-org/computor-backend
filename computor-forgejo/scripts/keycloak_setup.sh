#!/bin/sh
set -e

# Fixed client id — Forgejo always gets its own dedicated Keycloak client,
# distinct from the backend's (its redirect URIs are different). Not configurable
# on purpose: a custom value here is only ever a footgun.
CLIENT_ID="forgejo"
REDIRECT_URI="${FORGEJO_ROOT_URL}/user/oauth2/Keycloak/callback"
DISCOVER_URL="${KEYCLOAK_INTERNAL_URL}/realms/${KEYCLOAK_REALM}/.well-known/openid-configuration"

echo "=== Forgejo-Keycloak OIDC Setup ==="
echo "Keycloak : ${KEYCLOAK_INTERNAL_URL}  realm=${KEYCLOAK_REALM}"
echo "Client ID: ${CLIENT_ID}"
echo "Redirect : ${REDIRECT_URI}"

# Step 1 — admin token
TOKEN=$(wget -qO- \
  --post-data "grant_type=password&username=${KEYCLOAK_ADMIN}&password=${KEYCLOAK_ADMIN_PASSWORD}&client_id=admin-cli" \
  "${KEYCLOAK_INTERNAL_URL}/realms/master/protocol/openid-connect/token" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
[ -z "${TOKEN}" ] && { echo "ERROR: Keycloak admin auth failed"; exit 1; }

# Step 2 — create or fetch existing client
CLIENTS=$(wget -qO- \
  --header "Authorization: Bearer ${TOKEN}" \
  "${KEYCLOAK_INTERNAL_URL}/admin/realms/${KEYCLOAK_REALM}/clients?clientId=${CLIENT_ID}&search=false")
INTERNAL_ID=$(echo "${CLIENTS}" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

if [ -n "${INTERNAL_ID}" ]; then
  echo "Client '${CLIENT_ID}' already exists (id=${INTERNAL_ID}) — fetching secret"
  SECRET=$(wget -qO- \
    --header "Authorization: Bearer ${TOKEN}" \
    "${KEYCLOAK_INTERNAL_URL}/admin/realms/${KEYCLOAK_REALM}/clients/${INTERNAL_ID}/client-secret" \
    | grep -o '"value":"[^"]*' | cut -d'"' -f4)
else
  echo "Creating Keycloak client '${CLIENT_ID}'..."
  # 64 hex chars from /dev/urandom — busybox only (the forgejo image has no openssl).
  SECRET="$(tr -dc 'a-f0-9' < /dev/urandom | head -c 64)"
  cat > /tmp/kc_client.json << EOF
{
  "clientId": "${CLIENT_ID}",
  "name": "computor forgejo OIDC",
  "enabled": true,
  "protocol": "openid-connect",
  "publicClient": false,
  "clientAuthenticatorType": "client-secret",
  "secret": "${SECRET}",
  "redirectUris": ["${REDIRECT_URI}"],
  "webOrigins": ["+"],
  "standardFlowEnabled": true,
  "directAccessGrantsEnabled": false,
  "serviceAccountsEnabled": false,
  "attributes": {"post.logout.redirect.uris": "+"}
}
EOF
  wget -qO /dev/null \
    --header "Authorization: Bearer ${TOKEN}" \
    --header "Content-Type: application/json" \
    --post-file /tmp/kc_client.json \
    "${KEYCLOAK_INTERNAL_URL}/admin/realms/${KEYCLOAK_REALM}/clients" \
    || { echo "ERROR: Failed to create Keycloak client"; exit 1; }
  echo "Client '${CLIENT_ID}' created."
fi

# Step 3 — register OIDC auth source in Forgejo (idempotent)
echo "Registering OIDC source in Forgejo (auto-discover: ${DISCOVER_URL})..."
forgejo admin auth add-oauth \
  --name Keycloak \
  --provider openidConnect \
  --key "${CLIENT_ID}" \
  --secret "${SECRET}" \
  --auto-discover-url "${DISCOVER_URL}" \
  --scopes "email profile" 2>&1 \
  || echo "  Note: OIDC auth source may already exist — skipping."

echo "=== Setup complete ==="
