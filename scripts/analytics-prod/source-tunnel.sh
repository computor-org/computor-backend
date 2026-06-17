#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

if [ -n "${ANALYTICS_SOURCE_TUNNEL_ENV_FILE:-}" ] && [ -f "$ANALYTICS_SOURCE_TUNNEL_ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$ANALYTICS_SOURCE_TUNNEL_ENV_FILE"
    set +a
fi

mode="${1:-ensure}"

if [ "${ANALYTICS_SOURCE_TUNNEL_ENABLED:-false}" != "true" ]; then
    [ "$mode" = "status" ] && echo "analytics_source_tunnel=disabled"
    exit 0
fi

: "${ANALYTICS_SOURCE_TUNNEL_SSH_TARGET:?must be set in .env}"
: "${ANALYTICS_SOURCE_TUNNEL_REMOTE_HOST:=127.0.0.1}"
: "${ANALYTICS_SOURCE_TUNNEL_REMOTE_PORT:=5432}"
: "${ANALYTICS_SOURCE_TUNNEL_LOCAL_PORT:=15432}"

bind="${ANALYTICS_SOURCE_TUNNEL_BIND:-}"
if [ -z "$bind" ]; then
    bind="$(docker network inspect computor-network \
        --format '{{(index .IPAM.Config 0).Gateway}}')"
fi

ssh_args=(
    -o BatchMode=yes
    -o ExitOnForwardFailure=yes
    -o ServerAliveInterval=30
    -o ServerAliveCountMax=3
)

if [ -n "${ANALYTICS_SOURCE_TUNNEL_IDENTITY_FILE:-}" ]; then
    ssh_args+=(-i "$ANALYTICS_SOURCE_TUNNEL_IDENTITY_FILE")
fi

if [ "${ANALYTICS_SOURCE_TUNNEL_GSSAPI:-true}" = "true" ]; then
    ssh_args+=(
        -o GSSAPIAuthentication=yes
        -o GSSAPIDelegateCredentials=yes
    )
fi

forward="${bind}:${ANALYTICS_SOURCE_TUNNEL_LOCAL_PORT}:${ANALYTICS_SOURCE_TUNNEL_REMOTE_HOST}:${ANALYTICS_SOURCE_TUNNEL_REMOTE_PORT}"
pattern="${forward} ${ANALYTICS_SOURCE_TUNNEL_SSH_TARGET}"

is_listening() {
    ss -ltn "sport = :${ANALYTICS_SOURCE_TUNNEL_LOCAL_PORT}" \
        | awk '{print $4}' \
        | grep -Eq "(^|:)${ANALYTICS_SOURCE_TUNNEL_LOCAL_PORT}$"
}

case "$mode" in
    ensure)
        if is_listening; then
            echo "analytics_source_tunnel=already-listening"
            exit 0
        fi
        ssh "${ssh_args[@]}" -f -N -L "$forward" "$ANALYTICS_SOURCE_TUNNEL_SSH_TARGET"
        echo "analytics_source_tunnel=started bind=${bind} port=${ANALYTICS_SOURCE_TUNNEL_LOCAL_PORT}"
        ;;
    foreground)
        exec ssh "${ssh_args[@]}" -N -L "$forward" "$ANALYTICS_SOURCE_TUNNEL_SSH_TARGET"
        ;;
    status)
        if is_listening; then
            echo "analytics_source_tunnel=listening bind=${bind} port=${ANALYTICS_SOURCE_TUNNEL_LOCAL_PORT}"
        else
            echo "analytics_source_tunnel=stopped bind=${bind} port=${ANALYTICS_SOURCE_TUNNEL_LOCAL_PORT}"
            exit 1
        fi
        ;;
    stop)
        pkill -f "$pattern" 2>/dev/null || true
        echo "analytics_source_tunnel=stopped"
        ;;
    *)
        echo "usage: $0 [ensure|foreground|status|stop]" >&2
        exit 2
        ;;
esac
