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

# A schedule whose time passed while the system was down still fires if it is
# at most this overdue; beyond that it is recorded as missed instead — never
# surprise-update long after the maintenance window the admin picked.
SCHEDULE_GRACE_SECONDS=3600

rcli() {
    redis-cli -h redis -a "$REDIS_PASSWORD" --no-auth-warning "$@"
}

log() { echo "[updater] $*"; }

write_schedule_result() { # $1=outcome $2=scheduled_at $3=detail
    rcli HSET update:schedule:result \
        outcome "$1" \
        scheduled_at "$2" \
        resolved_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        detail "$3" >/dev/null 2>&1
    rcli EXPIRE update:schedule:result 604800 >/dev/null 2>&1
}

# Fire a scheduled update when its time has come: claim the schedule atomically
# (RENAME loses to a concurrent cancel), then enqueue exactly what the API's
# manual trigger enqueues — the BLPOP below picks it up on this same iteration.
check_schedule() {
    EPOCH=$(rcli HGET update:schedule scheduled_at_epoch 2>/dev/null)
    case "$EPOCH" in ''|*[!0-9]*) return;; esac
    NOW=$(date -u +%s)
    [ "$NOW" -lt "$EPOCH" ] && return

    # Atomic claim: fails if a concurrent DELETE /schedule already won.
    if ! rcli RENAME update:schedule update:schedule:claimed >/dev/null 2>&1; then
        return
    fi
    SCHED_AT=$(rcli HGET update:schedule:claimed scheduled_at 2>/dev/null)
    SCHED_BY=$(rcli HGET update:schedule:claimed scheduled_by 2>/dev/null)
    SCHED_BY_NAME=$(rcli HGET update:schedule:claimed scheduled_by_name 2>/dev/null)
    rcli DEL update:schedule:claimed >/dev/null 2>&1

    if [ $((NOW - EPOCH)) -gt "$SCHEDULE_GRACE_SECONDS" ]; then
        log "scheduled update for $SCHED_AT missed (overdue past grace window)"
        write_schedule_result missed "$SCHED_AT" \
            "The system was unavailable at the scheduled time; the update was not run."
        return
    fi

    if ! rcli SET update:lock "sched-$(date -u +%s)" NX EX 7200 | grep -q OK; then
        log "scheduled update for $SCHED_AT skipped — update lock already held"
        write_schedule_result skipped_lock "$SCHED_AT" \
            "Another update was already in progress at the scheduled time."
        return
    fi

    TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    log "scheduled update for $SCHED_AT firing"
    rcli DEL update:state >/dev/null 2>&1
    rcli HSET update:state \
        status "requested" \
        phase "" \
        message "Scheduled update firing" \
        requested_by "${SCHED_BY:-schedule}" \
        requested_by_name "${SCHED_BY_NAME:-Scheduled update}" \
        requested_at "$TS" \
        error "" >/dev/null 2>&1
    rcli LPUSH update:queue "{\"requested_by\":\"${SCHED_BY:-schedule}\",\"requested_at\":\"$TS\",\"scheduled\":true}" >/dev/null 2>&1
    write_schedule_result fired "$SCHED_AT" "The scheduled update was started."
}

SELF_IMAGE=$(docker inspect --format '{{.Image}}' "$(hostname)" 2>/dev/null || echo "computor-updater:latest")
log "watcher started (image ${SELF_IMAGE}, repo ${COMPUTOR_REPO_DIR})"

while true; do
    rcli HSET update:agent last_seen "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null 2>&1
    rcli EXPIRE update:agent 90 >/dev/null 2>&1

    check_schedule

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
