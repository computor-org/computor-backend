#!/usr/bin/env bash
# Host-side disk guard for Coder workspace volumes (coder-home-*, coder-scratch-*).
#
# Why host-side: the volumes live on the worker's docker data root (overlay2 on
# ext4 has no per-volume quota), and measuring them needs the host path that
# only root on the worker sees. The coder temporal worker cannot `du` a volume
# through the docker socket without starting a helper container per volume.
#
# For every workspace volume larger than COMPUTOR_HOME_LIMIT_GIB: log + alert,
# and stop the running containers that mount it (docker stop; Coder then shows
# the workspace as stopped/unhealthy and the owner must clean up before the
# next start pushes it over again). Nothing is deleted.
#
# Env (from /etc/default/computor-home-watchdog via the systemd unit):
#   COMPUTOR_HOME_LIMIT_GIB   limit per volume in GiB (default 10)
#   COMPUTOR_HOME_WARN_GIB    log a warning above this (default 80% of limit)
#   COMPUTOR_HOME_ALERT_URL   optional; POSTed a JSON {"text": ...} per breach
#   COMPUTOR_HOME_DRY_RUN     "true" = report only, never stop containers
set -euo pipefail

limit_gib="${COMPUTOR_HOME_LIMIT_GIB:-10}"
warn_gib="${COMPUTOR_HOME_WARN_GIB:-$(( limit_gib * 8 / 10 ))}"
alert_url="${COMPUTOR_HOME_ALERT_URL:-}"
dry_run="${COMPUTOR_HOME_DRY_RUN:-false}"
limit_bytes=$(( limit_gib * 1024 * 1024 * 1024 ))
warn_bytes=$(( warn_gib * 1024 * 1024 * 1024 ))

alert() {
    logger -t computor-home-watchdog -p user.warning -- "$1"
    echo "$1" >&2
    if [ -n "$alert_url" ]; then
        text=${1//\\/\\\\}; text=${text//\"/\\\"}
        curl -fsS -m 10 -H 'Content-Type: application/json' \
            -d "{\"text\": \"$(hostname): ${text}\"}" "$alert_url" >/dev/null || true
    fi
}

breaches=0
while read -r volume; do
    case "$volume" in coder-home-*|coder-scratch-*) ;; *) continue ;; esac
    mountpoint=$(docker volume inspect --format '{{.Mountpoint}}' "$volume")
    [ -d "$mountpoint" ] || continue
    # -x: stay on this filesystem; apparent size would undercount sparse abuse.
    used=$(du -sx --block-size=1 "$mountpoint" 2>/dev/null | cut -f1)
    used=${used:-0}
    used_gib=$(( used / 1024 / 1024 / 1024 ))
    if [ "$used" -gt "$limit_bytes" ]; then
        breaches=$(( breaches + 1 ))
        containers=$(docker ps -q --filter "volume=${volume}" | tr '\n' ' ')
        if [ "$dry_run" = "true" ] || [ -z "${containers// /}" ]; then
            alert "volume ${volume} uses ${used_gib} GiB > ${limit_gib} GiB (running: ${containers:-none}; not stopped)"
        else
            # shellcheck disable=SC2086
            docker stop --time 30 $containers >/dev/null
            alert "volume ${volume} uses ${used_gib} GiB > ${limit_gib} GiB: stopped ${containers}"
        fi
    elif [ "$used" -gt "$warn_bytes" ]; then
        logger -t computor-home-watchdog -p user.notice -- \
            "volume ${volume} uses ${used_gib} GiB (warn ${warn_gib}, limit ${limit_gib})"
    fi
done < <(docker volume ls -q)

echo "computor-home-watchdog: ${breaches} volume(s) over ${limit_gib} GiB"
