#!/usr/bin/env bash
# Host-side operations for the Computor coder worker.
#
# The coder worker (temporal-worker-coder) reaches Docker only through
# coder-worker-socket-proxy, which refuses container create and exec: with
# those, a Docker API client is root on the host whatever proxy sits in front
# (a privileged container with / mounted). The two operations that needed
# them run here instead, as root, on request from the worker:
#
#   chown-volume  volume=<coder-home-*|coder-scratch-*>
#       chown -R 1000:1000 the volume's contents from a throwaway container
#       (no network, only the file capabilities chown needs).
#   registry-gc   keep=<n> repo=<name>...
#       drop all but the newest <n> generated version tags (vYYYYMMDD-HHMMSS)
#       of each repo from the local registry, then one
#       `registry garbage-collect --delete-untagged` pass.
#
# Spool (created by computor-coder-hostops.tmpfiles; the worker mounts the
# directory at /hostops and the protocol is described in
# computor_backend/tasks/coder_hostops.py):
#   staging/ requests/ results/   owned by the worker uid (1000)
#   .work/                        root only: claimed requests, answers
#   registry.lock                 shared by worker pushes, exclusive here
#
# Everything read from the spool is untrusted: names are checked against
# fixed patterns, symlinks and non-regular files are refused, and invalid
# values are never echoed back.
#
# Env (from /etc/default/computor-coder-hostops via the systemd unit):
#   COMPUTOR_HOSTOPS_DIR          spool (default /var/lib/computor/coder-hostops)
#   COMPUTOR_REGISTRY_CONTAINER   registry container (default computor-coder-registry)
#   COMPUTOR_REPAIR_IMAGE         image for the chown (default: alpine 3.24.2,
#                                 pinned by digest; a tag could be moved by any
#                                 Docker client on this host, the digest cannot)
#   COMPUTOR_REGISTRY_LOCK_WAIT   seconds to wait for running pushes (default 1800)
set -uo pipefail
export LC_ALL=C

dir="${COMPUTOR_HOSTOPS_DIR:-/var/lib/computor/coder-hostops}"
registry="${COMPUTOR_REGISTRY_CONTAINER:-computor-coder-registry}"
# alpine:3.24.2 = alpine:3 on 2026-10-15 (OCI index digest from Docker Hub).
repair_image="${COMPUTOR_REPAIR_IMAGE:-alpine:3.24.2@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6}"
lock_wait="${COMPUTOR_REGISTRY_LOCK_WAIT:-1800}"
docker="${DOCKER:-docker}"

repo_root=/var/lib/registry/docker/registry/v2/repositories
id_re='^[0-9a-f]{32}$'
volume_re='^coder-(home|scratch)-[A-Za-z0-9][A-Za-z0-9_.-]*$'
repo_re='^[a-z0-9]+([._-][a-z0-9]+)*(/[a-z0-9]+([._-][a-z0-9]+)*)*$'
version_re='^v[0-9]{8}-[0-9]{6}(-[0-9a-f]{6})?$'

log() { logger -t computor-coder-hostops -- "$1" 2>/dev/null || true; echo "$1" >&2; }
one_line() { local s=${1//$'\n'/ | }; printf '%s' "${s:0:1000}"; }
answer_error() { echo "status=error"; echo "message=$(one_line "$1")"; }

chown_volume() {
    local volume=$1 driver opts err
    if ! [[ $volume =~ $volume_re ]]; then
        answer_error "not a workspace volume name"; return
    fi
    if ! driver=$("$docker" volume inspect --format '{{.Driver}}' -- "$volume" 2>/dev/null); then
        answer_error "volume '$volume' does not exist"; return
    fi
    opts=$("$docker" volume inspect --format '{{json .Options}}' -- "$volume" 2>/dev/null)
    # A local volume with driver options can be a bind mount of any host path
    # (o=bind,device=/...); workspace volumes never have options.
    if [ "$driver" != local ] || { [ "$opts" != null ] && [ "$opts" != '{}' ]; }; then
        answer_error "volume '$volume' is not a plain local volume; refusing"; return
    fi
    if err=$("$docker" run --rm --network none --log-driver none \
            --cap-drop ALL --cap-add CHOWN --cap-add DAC_OVERRIDE \
            --cap-add DAC_READ_SEARCH --cap-add FOWNER \
            --security-opt no-new-privileges \
            -v "$volume:/vol" "$repair_image" chown -R 1000:1000 /vol 2>&1 >/dev/null); then
        log "chown-volume $volume: ok"
        echo "status=ok"; echo "message=ownership of '$volume' reset to uid 1000"
    else
        log "chown-volume $volume: failed: $err"
        answer_error "chown failed: $err"
    fi
}

registry_gc() {
    local keep=$1; shift
    local repo tags tag paths=() removed=() out code tail
    if ! [[ $keep =~ ^[1-9][0-9]?$ ]]; then
        answer_error "invalid keep count"; return
    fi
    for repo in "$@"; do
        if ! [[ $repo =~ $repo_re ]]; then
            answer_error "invalid repository name"; return
        fi
    done
    exec 9<"$dir/registry.lock" || { answer_error "cannot open registry.lock"; return; }
    if ! flock -x -w "$lock_wait" 9; then
        exec 9<&-
        answer_error "a registry push held the lock for ${lock_wait}s; collection skipped"; return
    fi
    for repo in "$@"; do
        tags=$("$docker" exec "$registry" ls -1 "$repo_root/$repo/_manifests/tags" 2>/dev/null) \
            || continue  # repo not (yet) in the registry
        while IFS= read -r tag; do
            [ -n "$tag" ] || continue
            paths+=("$repo_root/$repo/_manifests/tags/$tag")
            removed+=("$repo:$tag")
        done < <(grep -E "$version_re" <<<"$tags" | sort -r | tail -n "+$((keep + 1))")
    done
    echo "status=ok"
    if [ ${#paths[@]} -eq 0 ]; then
        echo "message=nothing to remove"
        exec 9<&-
        return
    fi
    if ! out=$("$docker" exec "$registry" rm -rf "${paths[@]}" 2>&1); then
        exec 9<&-
        answer_error "registry tag removal failed: $out"; return
    fi
    printf 'removed=%s\n' "${removed[@]}"
    out=$("$docker" exec "$registry" registry garbage-collect --delete-untagged \
        /etc/docker/registry/config.yml 2>&1)
    code=$?
    exec 9<&-
    tail=$(tail -n 3 <<<"$out")
    echo "gc=exit=$code: $(one_line "$tail")"
    if [ "$code" -ne 0 ]; then
        echo "status=error"; echo "message=registry garbage-collect failed"
    fi
    log "registry-gc: removed ${#removed[@]} tag(s), gc exit=$code"
}

handle() {  # handle <claimed request file>
    local action="" volume="" keep="" repos=() key value
    while IFS='=' read -r key value; do
        case $key in
            action) action=$value ;;
            volume) volume=$value ;;
            keep) keep=$value ;;
            repo) repos+=("$value") ;;
        esac
    done < <(head -c 4096 -- "$1")
    case $action in
        chown-volume) chown_volume "$volume" ;;
        registry-gc) registry_gc "$keep" "${repos[@]}" ;;
        *) answer_error "unknown action" ;;
    esac
}

shopt -s nullglob
install -d -m 0700 "$dir/.work"
for request in "$dir"/requests/*.req; do
    id=$(basename -- "$request" .req)
    [[ $id =~ $id_re ]] || continue
    work="$dir/.work/$id"
    # Claim: once moved into the root-only directory, the worker can no
    # longer swap it. A failed move means the worker withdrew it.
    mv -T -- "$request" "$work" 2>/dev/null || continue
    answer="$dir/.work/$id.out"
    if [ -L "$work" ] || [ ! -f "$work" ]; then
        answer_error "request is not a regular file" >"$answer"
    else
        handle "$work" >"$answer"
    fi
    rm -rf -- "$work"
    chmod 0644 "$answer"
    # The worker reads the last status= line, so a later failure wins.
    mv -T -- "$answer" "$dir/results/$id" || log "could not deliver result $id"
done
# Drop anything that is not a request, so a stray file cannot keep the path
# unit triggering. Requests that arrived meanwhile stay for the next run.
find "$dir/requests" -mindepth 1 -maxdepth 1 ! -regex '.*/[0-9a-f]\{32\}\.req' \
    -exec rm -rf -- {} + 2>/dev/null
exit 0
