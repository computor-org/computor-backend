#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/ops/docker/docker-compose.analytics-instance.yaml"

ANALYTICS_LOCAL_DATA_ROOT="${ANALYTICS_LOCAL_DATA_ROOT:-/tmp/computor-analytics-local}"

ANALYTICS_LOCAL_SOURCE_PROJECT="${ANALYTICS_LOCAL_SOURCE_PROJECT:-computor-analytics-source}"
ANALYTICS_LOCAL_BLUE_PROJECT="${ANALYTICS_LOCAL_BLUE_PROJECT:-computor-analytics-blue}"

ANALYTICS_LOCAL_POSTGRES_USER="${ANALYTICS_LOCAL_POSTGRES_USER:-computor}"
ANALYTICS_LOCAL_POSTGRES_PASSWORD="${ANALYTICS_LOCAL_POSTGRES_PASSWORD:-computor_secret}"
ANALYTICS_LOCAL_POSTGRES_DB="${ANALYTICS_LOCAL_POSTGRES_DB:-computor}"

ANALYTICS_LOCAL_SOURCE_POSTGRES_PORT="${ANALYTICS_LOCAL_SOURCE_POSTGRES_PORT:-55432}"
ANALYTICS_LOCAL_SOURCE_REDIS_PORT="${ANALYTICS_LOCAL_SOURCE_REDIS_PORT:-56379}"
ANALYTICS_LOCAL_SOURCE_MINIO_API_PORT="${ANALYTICS_LOCAL_SOURCE_MINIO_API_PORT:-59000}"
ANALYTICS_LOCAL_SOURCE_MINIO_CONSOLE_PORT="${ANALYTICS_LOCAL_SOURCE_MINIO_CONSOLE_PORT:-59001}"

ANALYTICS_LOCAL_BLUE_POSTGRES_PORT="${ANALYTICS_LOCAL_BLUE_POSTGRES_PORT:-55433}"
ANALYTICS_LOCAL_BLUE_REDIS_PORT="${ANALYTICS_LOCAL_BLUE_REDIS_PORT:-56380}"
ANALYTICS_LOCAL_BLUE_MINIO_API_PORT="${ANALYTICS_LOCAL_BLUE_MINIO_API_PORT:-59002}"
ANALYTICS_LOCAL_BLUE_MINIO_CONSOLE_PORT="${ANALYTICS_LOCAL_BLUE_MINIO_CONSOLE_PORT:-59003}"

ANALYTICS_LOCAL_READER_USER="analytics_reader"
ANALYTICS_LOCAL_READER_PASSWORD="analytics_reader_secret"

compose_instance() {
    local project="$1"
    local root="$2"
    local postgres_port="$3"
    local redis_port="$4"
    local minio_api_port="$5"
    local minio_console_port="$6"
    shift 6

    ANALYTICS_LOCAL_INSTANCE_DATA_ROOT="$root" \
    ANALYTICS_LOCAL_POSTGRES_PORT="$postgres_port" \
    ANALYTICS_LOCAL_REDIS_PORT="$redis_port" \
    ANALYTICS_LOCAL_MINIO_API_PORT="$minio_api_port" \
    ANALYTICS_LOCAL_MINIO_CONSOLE_PORT="$minio_console_port" \
    ANALYTICS_LOCAL_POSTGRES_USER="$ANALYTICS_LOCAL_POSTGRES_USER" \
    ANALYTICS_LOCAL_POSTGRES_PASSWORD="$ANALYTICS_LOCAL_POSTGRES_PASSWORD" \
    ANALYTICS_LOCAL_POSTGRES_DB="$ANALYTICS_LOCAL_POSTGRES_DB" \
    docker compose -p "$project" -f "$COMPOSE_FILE" "$@"
}

compose_source() {
    compose_instance \
        "$ANALYTICS_LOCAL_SOURCE_PROJECT" \
        "${ANALYTICS_LOCAL_DATA_ROOT}/source" \
        "$ANALYTICS_LOCAL_SOURCE_POSTGRES_PORT" \
        "$ANALYTICS_LOCAL_SOURCE_REDIS_PORT" \
        "$ANALYTICS_LOCAL_SOURCE_MINIO_API_PORT" \
        "$ANALYTICS_LOCAL_SOURCE_MINIO_CONSOLE_PORT" \
        "$@"
}

compose_blue() {
    compose_instance \
        "$ANALYTICS_LOCAL_BLUE_PROJECT" \
        "${ANALYTICS_LOCAL_DATA_ROOT}/blue" \
        "$ANALYTICS_LOCAL_BLUE_POSTGRES_PORT" \
        "$ANALYTICS_LOCAL_BLUE_REDIS_PORT" \
        "$ANALYTICS_LOCAL_BLUE_MINIO_API_PORT" \
        "$ANALYTICS_LOCAL_BLUE_MINIO_CONSOLE_PORT" \
        "$@"
}

wait_for_postgres() {
    local name="$1"
    local compose_fn="$2"

    for _ in $(seq 1 60); do
        if "$compose_fn" exec -T postgres pg_isready \
            -U "$ANALYTICS_LOCAL_POSTGRES_USER" \
            -d "$ANALYTICS_LOCAL_POSTGRES_DB" >/dev/null 2>&1; then
            echo "${name} postgres is ready"
            return 0
        fi
        sleep 1
    done

    echo "Timed out waiting for ${name} postgres" >&2
    return 1
}

psql_source_admin() {
    compose_source exec -T postgres psql \
        -v ON_ERROR_STOP=1 \
        -U "$ANALYTICS_LOCAL_POSTGRES_USER" \
        -d "$ANALYTICS_LOCAL_POSTGRES_DB" \
        "$@"
}

psql_source_reader() {
    compose_source exec -T \
        -e PGPASSWORD="$ANALYTICS_LOCAL_READER_PASSWORD" \
        postgres psql \
        -v ON_ERROR_STOP=1 \
        -h localhost \
        -U "$ANALYTICS_LOCAL_READER_USER" \
        -d "$ANALYTICS_LOCAL_POSTGRES_DB" \
        "$@"
}

assert_safe_data_root() {
    case "$ANALYTICS_LOCAL_DATA_ROOT" in
        /tmp/computor-analytics-local|/tmp/computor-analytics-local/*)
            return 0
            ;;
    esac

    if [[ "${COMPUTOR_ANALYTICS_LOCAL_CONFIRM_DELETE:-}" == "1" ]]; then
        return 0
    fi

    echo "Refusing to delete ANALYTICS_LOCAL_DATA_ROOT=${ANALYTICS_LOCAL_DATA_ROOT}" >&2
    echo "Set COMPUTOR_ANALYTICS_LOCAL_CONFIRM_DELETE=1 to remove a custom root." >&2
    return 1
}

remove_data_root() {
    assert_safe_data_root

    if [[ ! -d "$ANALYTICS_LOCAL_DATA_ROOT" ]]; then
        return 0
    fi

    docker run --rm \
        --volume "${ANALYTICS_LOCAL_DATA_ROOT}:/data-root" \
        busybox:1.36 \
        sh -c "find /data-root -mindepth 1 -maxdepth 1 -exec rm -rf {} +"

    rmdir "$ANALYTICS_LOCAL_DATA_ROOT"
}
