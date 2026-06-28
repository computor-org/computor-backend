#!/usr/bin/env bash
# Wait for every integration-stack service to be healthy, or time out.
#
# GitLab is the slow one (3-5 min cold); others settle in seconds.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}/.."

COMPOSE="docker compose -f docker-compose.integration.yaml --env-file .env.integration"

SERVICES=(postgres redis temporal-postgres temporal minio gitlab api)
# Workers have no healthcheck; they're considered ready once started.
# temporal-ui is optional and not gated on.

TIMEOUT_SECONDS="${WAIT_TIMEOUT:-600}"
INTERVAL=5
START=$(date +%s)

is_healthy() {
	local svc="$1"
	local cid
	cid="$($COMPOSE ps -q "$svc" 2>/dev/null || true)"
	if [ -z "$cid" ]; then
		return 1
	fi
	local status
	status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || echo unknown)"
	[ "$status" = "healthy" ] || [ "$status" = "running" ]
}

is_fully_healthy() {
	local svc="$1"
	local cid
	cid="$($COMPOSE ps -q "$svc" 2>/dev/null || true)"
	[ -n "$cid" ] || return 1
	local status
	status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$cid" 2>/dev/null || echo unknown)"
	[ "$status" = "healthy" ] || [ "$status" = "no-healthcheck" ]
}

echo "Waiting for integration stack (timeout: ${TIMEOUT_SECONDS}s)..."

while :; do
	ALL_OK=1
	for svc in "${SERVICES[@]}"; do
		if ! is_fully_healthy "$svc"; then
			ALL_OK=0
			echo "  pending: $svc"
		fi
	done

	if [ "$ALL_OK" = "1" ]; then
		echo "All services healthy."
		exit 0
	fi

	NOW=$(date +%s)
	if (( NOW - START > TIMEOUT_SECONDS )); then
		echo "Timed out waiting for services."
		$COMPOSE ps
		exit 1
	fi

	sleep "$INTERVAL"
done
