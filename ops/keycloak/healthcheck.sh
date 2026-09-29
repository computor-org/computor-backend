#!/bin/bash
# Keycloak readiness probe for the compose healthcheck (mounted read-only into
# the container; the Keycloak image has bash but no curl/wget).
#
# Healthy only on HTTP 200 from <relative-path>/health/ready on the management
# port. Do NOT grep the body for "UP": during startup/migration Keycloak answers
# 503 with overall "DOWN" while individual checks (e.g. GracefulShutdown) are
# already "UP", which would pass a body grep and let dependants (API, IdP setup)
# start against a Keycloak that is not ready.
#
# Env: KC_HTTP_RELATIVE_PATH (as used by Keycloak), KC_HEALTH_PROBE_HOST /
# KC_HEALTH_PROBE_PORT (defaults localhost:9000; overridable for tests).
set -u
host="${KC_HEALTH_PROBE_HOST:-localhost}"
port="${KC_HEALTH_PROBE_PORT:-9000}"
rel="${KC_HTTP_RELATIVE_PATH:-/}"
rel="${rel%/}"

exec 3<>"/dev/tcp/${host}/${port}" || exit 1
printf 'GET %s/health/ready HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n' "$rel" >&3
IFS= read -r -t 5 status_line <&3 || exit 1
status_line="${status_line%$'\r'}"
case "$status_line" in
    "HTTP/1."[01]" 200"|"HTTP/1."[01]" 200 "*) exit 0 ;;
    *) exit 1 ;;
esac
