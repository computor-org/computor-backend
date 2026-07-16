#!/bin/bash
# Updater watcher: heartbeat + queue poll. On an update request it launches a
# DETACHED sibling runner container (outside the compose project) so that the
# maintenance stop / final `compose up -d` — which may recreate THIS watcher —
# can never kill the process driving the update.
#
# Keep this file thin and stable: it ships baked into the updater image, so an
# old copy must keep working against newer repo scripts. The only contract with
# the repo is: source ops/lib/common.sh + ops/lib/update.sh, call
# `cmd_update_exec prod`. Both files are sourced fully into memory before the
# run starts, so the mid-run `git checkout` cannot corrupt the executing code.

set -u

RUNNER_NAME="computor-update-runner"

rcli() {
    redis-cli -h redis -a "$REDIS_PASSWORD" --no-auth-warning "$@"
}

log() { echo "[updater] $*"; }

SELF_IMAGE=$(docker inspect --format '{{.Image}}' "$(hostname)" 2>/dev/null || echo "computor-updater:latest")
log "watcher started (image ${SELF_IMAGE}, repo ${COMPUTOR_REPO_DIR})"

while true; do
    rcli HSET update:agent last_seen "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1
    rcli EXPIRE update:agent 90 >/dev/null 2>&1

    # BLPOP prints "<key>\n<value>" on a hit, nothing on timeout.
    REQ=$(rcli BLPOP update:queue 30 2>/dev/null | tail -1)
    if [ -z "$REQ" ] || [ "$REQ" = "update:queue" ]; then
        continue
    fi
    log "update request: $REQ"

    if docker inspect "$RUNNER_NAME" >/dev/null 2>&1; then
        log "runner already exists — ignoring duplicate request"
        continue
    fi

    docker run -d --rm --name "$RUNNER_NAME" \
        --network computor-network \
        --user "$(id -u):$(id -g)" \
        --group-add "${DOCKER_GID:-0}" \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v "${COMPUTOR_REPO_DIR}:${COMPUTOR_REPO_DIR}" \
        -w "${COMPUTOR_REPO_DIR}" \
        -e REDIS_PASSWORD \
        -e DOCKER_GID \
        -e HOME=/tmp \
        "$SELF_IMAGE" \
        bash -c "source '${COMPUTOR_REPO_DIR}/ops/lib/common.sh' && source '${COMPUTOR_REPO_DIR}/ops/lib/update.sh' && cmd_update_exec prod" \
        || { log "failed to launch runner"; continue; }

    log "runner launched — waiting for it to finish"
    while docker inspect "$RUNNER_NAME" >/dev/null 2>&1; do
        rcli HSET update:agent last_seen "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1
        rcli EXPIRE update:agent 90 >/dev/null 2>&1
        sleep 5
    done
    log "runner finished"
done
