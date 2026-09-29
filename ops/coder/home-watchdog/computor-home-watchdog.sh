#!/usr/bin/env bash
# Host-side disk guard for Coder workspaces: home/scratch volumes
# (coder-home-*, coder-scratch-*) and each workspace container's writable
# layer (/tmp, /var, ... — everything outside the volumes).
#
# This is monitoring plus enforcement after the fact, NOT a quota: between two
# runs (60 s via the timer) a workspace can still write at full disk speed.
# Real byte/inode quotas (XFS project quotas for the docker data root and the
# volumes) are the tracked follow-up; keep the docker data root on its own
# filesystem with headroom until then.
#
# Why host-side: the volumes live on the worker's docker data root (overlay2 on
# ext4 has no per-volume quota), and measuring them needs the host path that
# only root on the worker sees.
#
# Over a limit: log + alert and stop the running containers concerned (docker
# stop; Coder then shows the workspace as stopped/unhealthy). Nothing is
# deleted. Every volume/container is handled independently: an error on one is
# reported and the scan continues. Exit status 2 = enforcement incomplete.
#
# Env (from /etc/default/computor-home-watchdog via the systemd unit):
#   COMPUTOR_HOME_LIMIT_GIB    limit per volume in GiB (default 10)
#   COMPUTOR_HOME_WARN_GIB     log a notice above this (default 80% of limit)
#   COMPUTOR_LAYER_LIMIT_GIB   limit per container writable layer (default 5)
#   COMPUTOR_HOME_ALERT_URL    optional; POSTed a JSON {"text": ...} per event
#   COMPUTOR_HOME_DRY_RUN      "true" = report only, never stop containers
set -uo pipefail

limit_gib="${COMPUTOR_HOME_LIMIT_GIB:-10}"
warn_gib="${COMPUTOR_HOME_WARN_GIB:-$(( limit_gib * 8 / 10 ))}"
layer_gib="${COMPUTOR_LAYER_LIMIT_GIB:-5}"
alert_url="${COMPUTOR_HOME_ALERT_URL:-}"
dry_run="${COMPUTOR_HOME_DRY_RUN:-false}"
gib=$(( 1024 * 1024 * 1024 ))
limit_bytes=$(( limit_gib * gib ))
warn_bytes=$(( warn_gib * gib ))
layer_bytes=$(( layer_gib * gib ))

breaches=0
errors=0

alert() {
    logger -t computor-home-watchdog -p user.warning -- "$1" 2>/dev/null || true
    echo "$1" >&2
    if [ -n "$alert_url" ]; then
        local text=${1//\\/\\\\}
        text=${text//\"/\\\"}
        curl -fsS -m 10 -H 'Content-Type: application/json' \
            -d "{\"text\": \"$(hostname): ${text}\"}" "$alert_url" >/dev/null || true
    fi
}

fail() {  # one object could not be measured or enforced; keep scanning
    errors=$(( errors + 1 ))
    alert "ERROR: $1"
}

# stop_containers <what> <ids...>: stop each, report every failure.
stop_containers() {
    local what=$1
    shift
    local id stopped="" failed=""
    for id in "$@"; do
        if docker stop --time 30 "$id" >/dev/null 2>&1; then
            stopped="$stopped $id"
        else
            failed="$failed $id"
        fi
    done
    [ -n "$stopped" ] && alert "${what}: stopped${stopped}"
    [ -n "$failed" ] && fail "${what}: could not stop${failed}"
    return 0
}

if ! volumes=$(docker volume ls -q 2>&1); then
    fail "docker volume ls failed: ${volumes}"
    volumes=""
fi

for volume in $volumes; do
    case "$volume" in coder-home-*|coder-scratch-*) ;; *) continue ;; esac
    if ! mountpoint=$(docker volume inspect --format '{{.Mountpoint}}' "$volume" 2>&1) \
        || [ ! -d "$mountpoint" ]; then
        fail "volume ${volume}: cannot resolve mountpoint (${mountpoint})"
        continue
    fi
    # -x: stay on this filesystem; allocated blocks, not apparent size.
    if ! out=$(du -sx --block-size=1 "$mountpoint" 2>/dev/null) || [ -z "$out" ]; then
        fail "volume ${volume}: du failed"
        continue
    fi
    used=${out%%[[:space:]]*}
    case "$used" in ''|*[!0-9]*) fail "volume ${volume}: bad du output '${out}'"; continue ;; esac
    used_gib=$(( used / gib ))
    if [ "$used" -gt "$limit_bytes" ]; then
        breaches=$(( breaches + 1 ))
        if ! containers=$(docker ps -q --filter "volume=${volume}" 2>&1); then
            fail "volume ${volume} over limit (${used_gib} GiB) but listing its containers failed"
            continue
        fi
        what="volume ${volume} uses ${used_gib} GiB > ${limit_gib} GiB"
        if [ "$dry_run" = "true" ] || [ -z "$containers" ]; then
            alert "${what} (running: ${containers:-none}; not stopped)"
        else
            # shellcheck disable=SC2086
            stop_containers "$what" $containers
        fi
    elif [ "$used" -gt "$warn_bytes" ]; then
        logger -t computor-home-watchdog -p user.notice -- \
            "volume ${volume} uses ${used_gib} GiB (warn ${warn_gib}, limit ${limit_gib})" \
            2>/dev/null || true
    fi
done

# Writable layers of running workspace containers (label set by every template).
if ! workspaces=$(docker ps -q --filter "label=coder.workspace_id" 2>&1); then
    fail "docker ps (workspace containers) failed: ${workspaces}"
    workspaces=""
fi
for id in $workspaces; do
    if ! size=$(docker inspect --size --format '{{.SizeRw}}' "$id" 2>&1); then
        fail "container ${id}: cannot read writable-layer size (${size})"
        continue
    fi
    case "$size" in ''|*[!0-9]*) fail "container ${id}: bad SizeRw '${size}'"; continue ;; esac
    if [ "$size" -gt "$layer_bytes" ]; then
        breaches=$(( breaches + 1 ))
        what="container ${id} writable layer $(( size / gib )) GiB > ${layer_gib} GiB"
        if [ "$dry_run" = "true" ]; then
            alert "${what} (not stopped)"
        else
            stop_containers "$what" "$id"
        fi
    fi
done

echo "computor-home-watchdog: ${breaches} over limit, ${errors} error(s)"
if [ "$errors" -gt 0 ]; then
    alert "enforcement INCOMPLETE: ${errors} object(s) could not be measured or stopped"
    exit 2
fi
exit 0
