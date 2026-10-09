#!/bin/bash
#
# Self-update executor (./computor.sh update ...). Requires ops/lib/common.sh.
#
#   check   — compare local HEAD against the tracked remote branch (read-only)
#   status  — show the state of the last/current update run (from Redis)
#   run     — acquire the update lock and execute an update now (host CLI path)
#   exec    — the actual executor; invoked by `run` and by the updater sidecar
#
# The exec flow deliberately builds the new images BEFORE entering maintenance
# so downtime shrinks to stop + up + health check, and a broken compose config
# in the new tree is caught before anything stops. All state transitions are
# written to Redis (update:state) so the admin UI can follow along while the
# API itself is down.
#
# IMPORTANT contract for the updater sidecar: the watcher sources this file
# fully into memory and then calls cmd_update_exec, so the git checkout that
# happens mid-run can safely replace this file on disk. Keep cmd_update_exec's
# CLI stable — an OLD watcher must be able to drive a NEW repo's scripts.

[ -n "${_COMPUTOR_UPDATE_SOURCED:-}" ] && return 0
_COMPUTOR_UPDATE_SOURCED=1
# Also available when the executor is sourced directly by a watcher or test.
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/git.sh"

UPDATE_KEY_STATE="update:state"
UPDATE_KEY_LOCK="update:lock"
UPDATE_KEY_QUEUE="update:queue"
UPDATE_KEY_REMOTE="update:remote"
UPDATE_KEY_LOG="update:log"

UPDATE_LOCK_TTL=7200
UPDATE_HEALTH_TRIES=60   # x 5s = 5 min budget per service

# --- helpers ---------------------------------------------------------------

update_env_init() {
    load_env
    derive_public_urls "$1"
    pin_project_name
    assemble_compose_files "$1"
}

set_update_state() { # field value [field value ...]
    redis_cli HSET "$UPDATE_KEY_STATE" "$@" >/dev/null || true
}

ulog() {
    log "  $*"
    redis_cli RPUSH "$UPDATE_KEY_LOG" "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >/dev/null || true
    redis_cli LTRIM "$UPDATE_KEY_LOG" -500 -1 >/dev/null || true
    redis_cli EXPIRE "$UPDATE_KEY_LOG" 86400 >/dev/null || true
}

set_phase() { # phase [message]
    set_update_state status running phase "$1" message "${2:-}"
    ulog "phase: $1${2:+ — $2}"
}

# --- Keycloak version-change guard ------------------------------------------------
#
# Keycloak migrates its database on start and does NOT support downgrades: an old
# Keycloak happily reports ready on a newer schema (only a log warning), so the
# code-only rollback below would silently run e.g. 25.x on a 26-migrated DB.
# Patch releases migrate too (26.4.3, 26.6.1, ...), so ANY image-tag change counts.
# When the tag changes, the updater takes a verified dump while Keycloak is
# stopped, and on a later failure it keeps maintenance up and refuses the
# automatic code rollback, printing the restore procedure instead.

KEYCLOAK_COMPOSE_REL="ops/docker/docker-compose.keycloak.yaml"
KEYCLOAK_DB_SERVICE="keycloak-db"
KEYCLOAK_CONTAINER="computor-keycloak"

keycloak_image_tag_at() { # git-ref -> Keycloak image tag in that tree ("" if none)
    deployment_git show "$1:$KEYCLOAK_COMPOSE_REL" 2>/dev/null \
        | sed -n 's#^[[:space:]]*image:[[:space:]]*quay\.io/keycloak/keycloak:\([^@[:space:]]*\).*#\1#p' \
        | head -n 1
}

keycloak_update_decision() { # from-tag to-tag keycloak-enabled -> none|guard|downgrade
    local from="$1" to="$2" enabled="$3"
    if [ "$enabled" != "true" ] || [ -z "$from" ] || [ -z "$to" ] || [ "$from" = "$to" ]; then
        echo none
    elif [ "$(printf '%s\n%s\n' "$from" "$to" | sort -V | tail -n 1)" = "$from" ]; then
        # Target is older: the DB is (or may be) migrated past it. A dump taken now
        # would be of the newer schema, so only a restore of a pre-upgrade dump is safe.
        echo downgrade
    else
        echo guard
    fi
}

keycloak_dump_is_complete() { # dump.sql.gz -> 0 if a complete pg_dump of the keycloak DB
    local f="$1"
    [ -s "$f" ] || return 1
    gzip -t "$f" 2>/dev/null || return 1
    gzip -dc "$f" | grep -q '^CREATE DATABASE keycloak ' || return 1
    gzip -dc "$f" | tail -n 10 | grep -q '^-- PostgreSQL database dump complete' || return 1
}

keycloak_stop_verified() { # stop Keycloak; 0 only if it is verifiably not running
    local state
    compose stop keycloak >/dev/null 2>&1 || return 1
    # docker ps fails (non-zero) if the daemon cannot answer: never read that as "absent".
    state=$(docker ps -a --filter "name=^/${KEYCLOAK_CONTAINER}\$" --format '{{.State}}') || return 1
    case "$state" in
        exited|created|"") return 0 ;;   # "" = no container at all: nothing can write
        *) return 1 ;;
    esac
}

updater_state_dir() { # host-persistent updater state (dumps, recovery marker)
    echo "${SYSTEM_DEPLOYMENT_PATH:?}/updater"
}

updater_state_is_persistent() {
    # Created on the host by computor.sh up; visible in the runner only through the
    # bind mount watch.sh adds. Never create it here: inside a runner without the
    # mount that would silently write into the throwaway container.
    [ -f "$(updater_state_dir)/.host-persistent" ] && [ -w "$(updater_state_dir)" ]
}

keycloak_predump() { # dest.sql.gz ; Keycloak itself must already be stopped
    local dest="$1" tmp i
    updater_state_is_persistent || { ulog "updater state dir $(updater_state_dir) is missing, not writable or not host-persistent"; return 1; }
    case "$dest" in "$(updater_state_dir)"/*) ;; *) return 1 ;; esac
    mkdir -p "$(dirname "$dest")" || return 1
    tmp="${dest}.partial"
    compose up -d "$KEYCLOAK_DB_SERVICE" >/dev/null 2>&1 || return 1
    for ((i = 1; i <= 30; i++)); do
        compose exec -T "$KEYCLOAK_DB_SERVICE" pg_isready -U keycloak -p 5438 >/dev/null 2>&1 && break
        sleep 2
    done
    ( umask 077; set -o pipefail
      compose exec -T "$KEYCLOAK_DB_SERVICE" pg_dump -U keycloak -p 5438 --create -d keycloak | gzip > "$tmp" ) \
        || { rm -f "$tmp"; return 1; }
    keycloak_dump_is_complete "$tmp" || { rm -f "$tmp"; return 1; }
    mv -f "$tmp" "$dest"
}

# --- recovery marker ----------------------------------------------------------------
# Written before Keycloak can migrate its database, including a killed runner. While it
# exists, updates and 'maintenance exit' refuse to run; only 'update recover' (which
# health-checks the result) clears it. File = authoritative (host-persistent);
# Redis update:recovery = mirror for the admin UI.
UPDATE_KEY_RECOVERY="update:recovery"

recovery_marker_file() { echo "$(updater_state_dir)/recovery-required"; }

recovery_required() {
    [ -e "$(recovery_marker_file)" ] && return 0
    [ "$(redis_cli EXISTS "$UPDATE_KEY_RECOVERY" 2>/dev/null)" = "1" ]
}

recovery_marker_get() { # key -> value from the marker file
    sed -n "s/^$1=//p" "$(recovery_marker_file)" 2>/dev/null | head -n 1
}

write_recovery_marker() { # reason from-commit to-commit kc-from kc-to dump
    local f
    f="$(recovery_marker_file)"
    updater_state_is_persistent || return 1
    ( umask 077; printf 'reason=%s\nfrom_commit=%s\nto_commit=%s\nkeycloak_from=%s\nkeycloak_to=%s\ndump=%s\ncreated_at=%s\n' \
        "$1" "$2" "$3" "$4" "$5" "$6" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$f.tmp" && mv -f "$f.tmp" "$f" ) \
        || return 1
    redis_cli HSET "$UPDATE_KEY_RECOVERY" reason "$1" from_commit "$2" to_commit "$3" \
        keycloak_from "$4" keycloak_to "$5" dump "$6" >/dev/null || true
}

clear_recovery_marker() {
    redis_cli DEL "$UPDATE_KEY_RECOVERY" >/dev/null || return 1
    rm -f "$(recovery_marker_file)"
}

wait_for_keycloak() {
    local i
    for ((i = 1; i <= UPDATE_HEALTH_TRIES; i++)); do
        [ "$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$KEYCLOAK_CONTAINER" 2>/dev/null)" = "healthy" ] && return 0
        sleep 5
    done
    return 1
}

keycloak_schema_matches() {
    local got
    got=$(compose exec -T "$KEYCLOAK_DB_SERVICE" psql -X -U keycloak -p 5438 -d keycloak -Atc \
        'select version from migration_model order by update_time desc limit 1') || return 1
    [ "$got" = "$1" ] || { ulog "Keycloak schema is '${got}', expected '$1'"; return 1; }
}

keycloak_restore_dump() { # dump expected-version ; Keycloak must be stopped
    local dump="$1" want="$2" i
    keycloak_dump_is_complete "$dump" || { ulog "dump $dump missing or incomplete"; return 1; }
    compose up -d "$KEYCLOAK_DB_SERVICE" >/dev/null 2>&1 || return 1
    for ((i = 1; i <= 30; i++)); do
        compose exec -T "$KEYCLOAK_DB_SERVICE" pg_isready -U keycloak -p 5438 >/dev/null 2>&1 && break
        sleep 2
    done
    compose exec -T "$KEYCLOAK_DB_SERVICE" psql -X -v ON_ERROR_STOP=1 -U keycloak -p 5438 -d postgres -q \
        -c 'DROP DATABASE IF EXISTS keycloak WITH (FORCE)' >/dev/null || return 1
    # Database-only pg_dump avoids pg_dumpall's duplicate-role errors. Every SQL
    # error is fatal: a readable migration_model alone cannot prove a full restore.
    ( set -o pipefail; gzip -dc "$dump" | compose exec -T "$KEYCLOAK_DB_SERVICE" \
        psql -X -v ON_ERROR_STOP=1 -U keycloak -p 5438 -d postgres -q ) || return 1
    keycloak_schema_matches "$want"
}

# ./computor.sh update recover prod restore|keep-new
#   restore  : stop Keycloak, check out the pre-upgrade commit, restore the pre-upgrade
#              dump (verified schema version), rebuild, start, health-check
#   keep-new : keep the new version (fixed forward), start, health-check
# Maintenance and the marker are cleared only when every health check passes.
cmd_update_recover() {
    ENVIRONMENT="${1:-prod}"
    local mode="${2:-}" branch dump from_commit kc_from kc_to expected
    [ "$ENVIRONMENT" = "prod" ] || die "Recovery only applies to prod."
    update_env_init "$ENVIRONMENT"
    case "$mode" in restore|keep-new) ;; *) die "Usage: $0 update recover prod restore|keep-new" ;; esac
    recovery_required || die "No update recovery is pending."
    update_access_preflight
    if [ "$(redis_cli SET "$UPDATE_KEY_LOCK" "recover-$$" NX EX $UPDATE_LOCK_TTL)" != "OK" ]; then
        die "An update is in progress (update:lock is held)."
    fi
    branch="${SYSTEM_REPO_BRANCH:-main}"
    dump=$(recovery_marker_get dump)
    from_commit=$(recovery_marker_get from_commit)
    kc_from=$(recovery_marker_get keycloak_from)
    kc_to=$(recovery_marker_get keycloak_to)

    recover_fail() {
        ulog "RECOVERY FAILED ($mode): $1 — maintenance stays up, recovery still required"
        set_update_state status failed error "$1" finished_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        redis_cli DEL "$UPDATE_KEY_LOCK" >/dev/null || true
        exit 1
    }

    set_update_state status running phase recovering message "Recovery (${mode})" error ""
    [ -n "$from_commit" ] && [ -n "$kc_from" ] && [ -n "$kc_to" ] \
        || recover_fail "host recovery marker lacks required metadata; do not bypass it"
    [ -z "$(deployment_git status --porcelain --untracked-files=no)" ] \
        || recover_fail "working tree has local changes; commit them before recovery"
    # Reestablish Redis state after a restart; the host route remains authoritative.
    set_redis_maintenance "1" "Update recovery is in progress."
    ensure_maintenance_page || recover_fail "cannot stage maintenance page"
    activate_traefik_maintenance || recover_fail "cannot activate maintenance route"
    if [ "$mode" = "restore" ]; then
        [ -n "$dump" ] && [ -n "$from_commit" ] && [ -n "$kc_from" ] \
            || recover_fail "recovery marker lacks dump/from_commit/keycloak_from (Redis-only marker?)"
        keycloak_dump_is_complete "$dump" || recover_fail "dump is missing or incomplete"
        [ "$(keycloak_image_tag_at "$from_commit")" = "$kc_from" ] \
            || recover_fail "pre-upgrade checkout does not match the recorded Keycloak version"
        keycloak_stop_verified || recover_fail "Keycloak did not stop cleanly"
        # A failed restore can leave a partial database. Never let keep-new accept
        # that database just because its schema row and HTTP health look correct.
        printf 'restore_started=1\n' >> "$(recovery_marker_file)" || recover_fail "cannot persist restore state"
        deployment_git checkout -q -B "$branch" "$from_commit" || recover_fail "checkout of ${from_commit} failed"
        keycloak_restore_dump "$dump" "$kc_from" || recover_fail "restoring ${dump} failed"
        ulog "Keycloak DB restored from ${dump} (schema ${kc_from})"
        expected="$kc_from"
    else
        [ "$(recovery_marker_get restore_started)" != "1" ] \
            || recover_fail "a restore was started; retry restore instead of accepting a possibly partial database"
        expected="$kc_to"
    fi
    [ "$(keycloak_image_tag_at HEAD)" = "$expected" ] \
        || recover_fail "current checkout does not use the expected Keycloak ${expected}"
    build_images || recover_fail "image build failed"
    compose up -d || recover_fail "'compose up' failed"
    wait_for_keycloak || recover_fail "Keycloak did not become healthy"
    keycloak_schema_matches "$expected" || recover_fail "Keycloak schema version mismatch"
    wait_for_api || recover_fail "API health check timed out"
    wait_for_frontend || recover_fail "frontend health check timed out"

    clear_recovery_marker || recover_fail "cannot clear recovery state"
    deactivate_traefik_maintenance
    set_redis_maintenance "0" ""
    set_update_state status success message "Recovery (${mode}) succeeded" error "" \
        finished_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    redis_cli DEL "$UPDATE_KEY_LOCK" >/dev/null || true
    ulog "Recovery (${mode}) succeeded; maintenance lifted."
}

keycloak_restore_instructions() { # dump from-commit from-tag
    cat <<INSTR
Keycloak was upgraded in place and its database may already be migrated.
Keycloak does not support downgrades; the previous code was NOT restored.
Maintenance mode stays active and further updates are blocked until recovery:
  ./computor.sh update recover prod restore    # restore $1, back to $2 (Keycloak $3)
  ./computor.sh update recover prod keep-new   # after fixing forward on the new version
Both health-check Keycloak, API and frontend before lifting maintenance.
INSTR
}

keycloak_block_rollback() { # reason dump from-commit from-tag to-commit to-tag ; never returns
    local line
    # The durable marker was installed before starting the new Keycloak.
    write_recovery_marker "$1" "$3" "$5" "$4" "$6" "$2" \
        || ulog "Could not update recovery reason; the pre-start marker remains in place."
    set_update_state keycloak_restore_dump "$2"
    while IFS= read -r line; do ulog "$line"; done < <(keycloak_restore_instructions "$2" "$3" "$4")
    fail_update "Update failed ($1) after the Keycloak ${4} -> new version switch; automatic rollback refused (Keycloak DB downgrade unsupported). Maintenance page stays up; pre-upgrade dump: $2. See the update log for the restore procedure."
}

# Tip commit of the tracked branch. The token (if any) goes through an inline
# credential helper that reads it from the environment — never argv or the URL.
git_remote_tip() {
    local url="$1" branch="$2"
    local -a cfg=()
    if [ -n "${SYSTEM_REPO_TOKEN:-}" ]; then
        # shellcheck disable=SC2016
        cfg=(-c 'credential.helper=!f() { echo "username=oauth2"; echo "password=$SYSTEM_REPO_TOKEN"; }; f')
    fi
    GIT_TERMINAL_PROMPT=0 git "${cfg[@]}" ls-remote "$url" "refs/heads/$branch" 2>/dev/null \
        | awk 'NR==1 {print $1}'
}

git_fetch_tracked() {
    local url="$1" branch="$2"
    local -a cfg=()
    if [ -n "${SYSTEM_REPO_TOKEN:-}" ]; then
        # shellcheck disable=SC2016
        cfg=(-c 'credential.helper=!f() { echo "username=oauth2"; echo "password=$SYSTEM_REPO_TOKEN"; }; f')
    fi
    GIT_TERMINAL_PROMPT=0 deployment_git "${cfg[@]}" fetch "$url" "$branch"
}

# API liveness via docker exec — identical from the host and from the runner
# container, and it implicitly proves the container is up. HEAD / returns 204
# once migrations (docker/api/startup.bash) are done and uvicorn serves.
wait_for_api() {
    local i
    for ((i = 1; i <= UPDATE_HEALTH_TRIES; i++)); do
        if compose exec -T uvicorn python3 -c '
import sys, urllib.request
req = urllib.request.Request("http://localhost:8000/", method="HEAD")
sys.exit(0 if urllib.request.urlopen(req, timeout=5).status < 500 else 1)
' >/dev/null 2>&1; then
            return 0
        fi
        sleep 5
    done
    return 1
}

wait_for_frontend() {
    local i
    for ((i = 1; i <= UPDATE_HEALTH_TRIES; i++)); do
        if compose exec -T frontend node -e '
fetch("http://localhost:3000/api/health")
  .then((r) => process.exit(r.ok ? 0 : 1))
  .catch(() => process.exit(1));
' >/dev/null 2>&1; then
            return 0
        fi
        sleep 5
    done
    return 1
}

# Rebuild all project images for the CURRENT checkout (used for both the new
# tree and a rollback — old trees rebuild almost entirely from cache).
#
# computor-base is unconditional: the checkout just moved, so its source layer is
# stale by definition. The standalone base images go through build_base_image, so
# an update only pays for the ones whose Dockerfile actually changed between the
# two checkouts — and, unlike the list this replaced, code-server and the MATLAB
# base are no longer skipped when they DID change.
build_images() {
    git_build_meta
    ulog "building computor-base (commit ${GIT_COMMIT}, built ${BUILD_TIME})"
    (cd "$REPO_ROOT" && docker build -f docker/base/Dockerfile -t computor-base:latest \
        --build-arg GIT_COMMIT="$GIT_COMMIT" --build-arg GIT_BRANCH="$GIT_BRANCH" \
        --build-arg BUILD_TIME="$BUILD_TIME" .) || return 1

    ulog "checking computor-testing-runtimes"
    build_base_image testing-runtimes computor-testing-runtimes:latest \
        docker/testing-runtimes/Dockerfile . || return 1

    if [ "${CODER_ENABLED:-}" = "true" ]; then
        ulog "checking computor-coder-runtime"
        build_base_image coder-runtime computor-coder-runtime:latest \
            docker/coder-runtime/Dockerfile . || return 1
        ulog "checking computor-code-server"
        build_base_image code-server computor-code-server:latest \
            docker/code-server-base/Dockerfile docker/code-server-base || return 1
    fi

    if [ "${MATLAB_ENABLED:-}" = "true" ] && [ "${MATLAB_BASE_IMAGE_MANAGED:-}" = "true" ]; then
        ulog "checking ${MATLAB_BASE_IMAGE}"
        build_base_image matlab "$MATLAB_BASE_IMAGE" docker/matlab/Dockerfile docker/matlab \
            --build-arg MATLAB_RELEASE="$MATLAB_RELEASE" || return 1
    fi

    ulog "building compose service images"
    compose build || return 1
}

# --- commands ----------------------------------------------------------------

update_access_preflight() {
    local git_dir path
    git_dir=$(deployment_git rev-parse --absolute-git-dir) \
        || die "Cannot read the deployment Git repository as $(id -un)."
    for path in "$REPO_ROOT" "$git_dir" "$git_dir/HEAD" "$git_dir/index"; do
        [ ! -e "$path" ] || [ -w "$path" ] || die "Cannot update $path as $(id -un).
Ask the deployment owner to prepare shared deployment access; no sudo to another user is required.
See ops/docs/DOCKER_SETUP.md (shared deployments)."
    done
}

cmd_update_check() {
    ENVIRONMENT="${1:-prod}"
    load_env
    local url="${SYSTEM_REPO_URL:-}" branch="${SYSTEM_REPO_BRANCH:-main}"
    [ -n "$url" ] || die "SYSTEM_REPO_URL is not set in .env"

    local local_head remote_tip
    local_head=$(deployment_git rev-parse HEAD) \
        || die "Cannot read the deployment Git repository as $(id -un)."
    remote_tip=$(git_remote_tip "$url" "$branch")
    [ -n "$remote_tip" ] || die "Could not read refs/heads/$branch from $url"

    log "Local HEAD:  ${YELLOW}${local_head}${NC}"
    log "Remote tip:  ${YELLOW}${remote_tip}${NC} (${branch})"
    if [ "$local_head" = "$remote_tip" ]; then
        log "${GREEN}Up to date.${NC}"
    else
        log "${YELLOW}Update available.${NC} Run: ./computor.sh update run prod"
        return 10
    fi
}

cmd_update_status() {
    ENVIRONMENT="${1:-prod}"
    update_env_init "$ENVIRONMENT"

    log "${BLUE}=== Update State (Redis) ===${NC}"
    redis_cli HGETALL "$UPDATE_KEY_STATE" | paste - - | sed 's/^/  /' || true
    local lock_ttl
    lock_ttl=$(redis_cli TTL "$UPDATE_KEY_LOCK")
    if [ -n "$lock_ttl" ] && [ "$lock_ttl" -gt 0 ] 2>/dev/null; then
        log "Lock: ${YELLOW}held${NC} (expires in ${lock_ttl}s)"
    else
        log "Lock: ${GREEN}free${NC}"
    fi
    if [ "$(redis_cli EXISTS update:agent)" = "1" ]; then
        log "Updater sidecar: ${GREEN}online${NC}"
    else
        log "Updater sidecar: ${YELLOW}offline${NC}"
    fi
    log "\n${BLUE}Recent update log:${NC}"
    redis_cli LRANGE "$UPDATE_KEY_LOG" -15 -1 | sed 's/^/  /' || true
}

cmd_update_run() {
    ENVIRONMENT="${1:-prod}"
    [ "$ENVIRONMENT" = "prod" ] || die "Self-update only supports prod (dev runs the API on the host)."
    update_env_init "$ENVIRONMENT"
    update_access_preflight

    if [ "$(redis_cli SET "$UPDATE_KEY_LOCK" "cli-$$" NX EX $UPDATE_LOCK_TTL)" != "OK" ]; then
        die "An update is already in progress (update:lock is held). See: ./computor.sh update status"
    fi
    redis_cli DEL "$UPDATE_KEY_STATE" >/dev/null || true
    set_update_state status requested requested_by "cli" requested_by_name "$(id -un) (CLI)" \
        requested_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    cmd_update_exec "$ENVIRONMENT"
}

cmd_update_exec() {
    ENVIRONMENT="${1:-prod}"
    [ "$ENVIRONMENT" = "prod" ] || die "Self-update only supports prod (dev runs the API on the host)."
    update_env_init "$ENVIRONMENT"
    update_access_preflight

    local url="${SYSTEM_REPO_URL:-}" branch="${SYSTEM_REPO_BRANCH:-main}"
    local from_commit to_commit maintenance_entered=0
    local kc_from="" kc_to="" kc_decision=none kc_dump="" kc_switched=0

    # Keep the sidecar (and socket-proxy, which traefik's docker provider needs)
    # alive through the maintenance stop — everything else goes down.
    MAINTENANCE_KEEP_SERVICES="traefik static-server redis socket-proxy updater"

    # Take the lock if nobody holds it (the API/`run` normally set it already).
    redis_cli SET "$UPDATE_KEY_LOCK" "exec-$$" NX EX $UPDATE_LOCK_TTL >/dev/null || true

    fail_update() { # message [status]
        local status="${2:-failed}"
        ulog "FAILED: $1"
        set_update_state status "$status" error "$1" finished_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        redis_cli DEL "$UPDATE_KEY_LOCK" >/dev/null || true
        exit 1
    }

    finish_update() { # status message
        if [ "$kc_switched" = "1" ]; then
            clear_recovery_marker || fail_update "Cannot clear recovery state; maintenance stays up."
        fi
        deactivate_traefik_maintenance
        set_redis_maintenance "0" ""
        redis_cli DEL "$UPDATE_KEY_REMOTE" >/dev/null || true
        set_update_state status "$1" message "$2" error "" \
            finished_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        redis_cli DEL "$UPDATE_KEY_LOCK" >/dev/null || true
        ulog "$2"
        # exit (not return): after the checkout the on-disk scripts belong to
        # the NEW version — never fall back into the outer script's remainder.
        exit 0
    }

    do_rollback() { # reason
        if [ "$kc_switched" = "1" ]; then
            keycloak_block_rollback "$1" "$kc_dump" "$from_commit" "$kc_from" "$to_commit" "$kc_to"
        fi
        set_phase rolling_back "Update failed ($1) — restoring ${from_commit}"
        if ! deployment_git checkout -q -B "$branch" "$from_commit"; then
            fail_update "Rollback checkout to ${from_commit} failed after: $1. Manual intervention required (maintenance page stays up): fix the checkout, then './computor.sh maintenance exit prod'."
        fi
        if ! build_images; then
            fail_update "Rollback image rebuild failed after: $1. Manual intervention required (maintenance page stays up)."
        fi
        if [ "$maintenance_entered" = "1" ]; then
            compose up -d || fail_update "Rollback 'compose up' failed after: $1. Manual intervention required (maintenance page stays up)."
            if ! wait_for_api; then
                fail_update "Rollback health check failed after: $1. Maintenance page stays up; inspect 'docker compose logs uvicorn', then './computor.sh maintenance exit prod'."
            fi
            finish_update rolled_back "Update failed ($1); rolled back to ${from_commit} and restored service."
        fi
        # Failure before any downtime (e.g. build): system never stopped.
        set_update_state status failed error "Update failed ($1). The system was never taken down; previous images were restored." \
            finished_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        redis_cli DEL "$UPDATE_KEY_LOCK" >/dev/null || true
        exit 1
    }

    set_update_state status running started_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" error ""

    # 1. preflight ------------------------------------------------------------
    set_phase preflight
    if recovery_required; then
        fail_update "Recovery required after a failed Keycloak upgrade ($(recovery_marker_get reason)); maintenance stays up. Run './computor.sh update recover prod restore|keep-new'."
    fi
    [ -n "$url" ] || fail_update "SYSTEM_REPO_URL is not set in .env"
    deployment_git rev-parse --git-dir >/dev/null 2>&1 \
        || fail_update "$REPO_ROOT is not a git repository"

    local dirty
    dirty=$(deployment_git status --porcelain --untracked-files=no)
    if [ -n "$dirty" ]; then
        if [ "${UPDATE_GIT_FORCE:-}" = "true" ]; then
            ulog "working tree dirty — discarding local changes (UPDATE_GIT_FORCE=true)"
            deployment_git reset --hard >/dev/null
        else
            fail_update "Working tree has local changes; refusing to update. Commit/stash them or set UPDATE_GIT_FORCE=true in .env. Dirty files: $(echo "$dirty" | awk '{print $2}' | tr '\n' ' ')"
        fi
    fi

    from_commit=$(deployment_git rev-parse HEAD)
    set_update_state from_commit "$from_commit"

    # 2. fetch ------------------------------------------------------------------
    set_phase checking "Fetching ${branch} from remote"
    git_fetch_tracked "$url" "$branch" || fail_update "git fetch from configured SYSTEM_REPO_URL failed"
    to_commit=$(deployment_git rev-parse FETCH_HEAD)
    set_update_state to_commit "$to_commit"

    if [ "$to_commit" = "$from_commit" ]; then
        finish_update success "Already up to date (${from_commit})."
    fi

    kc_from=$(keycloak_image_tag_at "$from_commit")
    kc_to=$(keycloak_image_tag_at "$to_commit")
    kc_decision=$(keycloak_update_decision "$kc_from" "$kc_to" "${KEYCLOAK_ENABLED:-}")
    if [ "$kc_decision" = "downgrade" ]; then
        fail_update "Refusing automated Keycloak downgrade ${kc_from} -> ${kc_to} (target ${to_commit}): Keycloak cannot run on a database migrated by a newer version. Nothing was changed. Restore a pre-upgrade dump of the Keycloak DB taken on ${kc_to} (restore procedure: see the Keycloak rollback section of PR #255 / the update log), then deploy ${to_commit} manually."
    fi
    if [ "$kc_decision" = "guard" ]; then
        ulog "Keycloak image changes ${kc_from} -> ${kc_to}: a verified DB dump is taken before start; no automatic rollback after it"
        set_update_state keycloak_from "$kc_from" keycloak_to "$kc_to"
    fi

    # 3. checkout ---------------------------------------------------------------
    set_phase checking_out "Checking out ${to_commit}"
    deployment_git checkout -q -B "$branch" FETCH_HEAD \
        || fail_update "git checkout of ${to_commit} failed"

    # New-tree preflight: catches broken compose interpolation (e.g. a new :?
    # variable missing from .env) BEFORE any downtime.
    if ! compose config -q; then
        deployment_git checkout -q -B "$branch" "$from_commit"
        fail_update "The new version's docker compose configuration is invalid with the current .env (checked out ${to_commit}, reverted). Compare .env against ops/environments/.env.common.template."
    fi

    # 4. build (services still up — no downtime yet) ------------------------------
    set_phase building "Building images for ${to_commit}"
    build_images || do_rollback "image build failed"

    # 5. maintenance ---------------------------------------------------------------
    set_phase entering_maintenance
    maintenance_entered=1
    set_redis_maintenance "1" "The system is being updated. We will be back in a few minutes."
    sleep 3
    ensure_maintenance_page || do_rollback "cannot stage maintenance page"
    activate_traefik_maintenance || do_rollback "cannot activate maintenance route"
    local service
    for service in $(get_stoppable_services); do
        compose stop "$service" >/dev/null 2>&1 && ulog "stopped: $service" || true
    done

    # 5b. Keycloak pre-upgrade dump (Keycloak is stopped: quiesced) ------------------
    if [ "$kc_decision" = "guard" ]; then
        kc_dump="$(updater_state_dir)/backups/keycloak/keycloak-pre-${kc_from}-to-${kc_to}-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
        set_phase keycloak_backup "Dumping the Keycloak DB before ${kc_from} -> ${kc_to}"
        # Nothing has run on the new Keycloak yet, so a plain rollback is still safe here.
        # A dump is only consistent if the old Keycloak can no longer write.
        keycloak_stop_verified || do_rollback "Keycloak did not stop cleanly; refusing to dump a live database"
        keycloak_predump "$kc_dump" || do_rollback "Keycloak pre-upgrade DB dump failed or incomplete"
        ulog "Keycloak DB dump verified: ${kc_dump}"
        set_update_state keycloak_dump "$kc_dump"
        write_recovery_marker "Keycloak upgrade awaiting health checks" "$from_commit" "$to_commit" "$kc_from" "$kc_to" "$kc_dump" \
            || do_rollback "cannot persist Keycloak recovery state"
        kc_switched=1
    fi

    # 6. start ---------------------------------------------------------------------
    set_phase starting "Starting services on ${to_commit}"
    compose up -d || do_rollback "'compose up' failed"

    # 7. health check ----------------------------------------------------------------
    if [ "$kc_switched" = "1" ]; then
        wait_for_keycloak || do_rollback "Keycloak health check timed out"
        keycloak_schema_matches "$kc_to" || do_rollback "Keycloak schema version mismatch"
    fi
    set_phase health_check "Waiting for the API (migrations run first)"
    wait_for_api || do_rollback "API health check timed out"
    set_phase health_check "Waiting for the frontend"
    wait_for_frontend || do_rollback "frontend health check timed out"

    # 8. finalize --------------------------------------------------------------------
    set_phase finalizing
    finish_update success "Updated ${from_commit} -> ${to_commit}."
}

dispatch_update() {
    local action="${1:-status}"
    shift || true
    case "$action" in
        check)  cmd_update_check "$@" ;;
        status) cmd_update_status "$@" ;;
        run)    cmd_update_run "$@" ;;
        exec)   cmd_update_exec "$@" ;;
        recover) cmd_update_recover "$@" ;;
        *)
            echo "Usage: $0 update {check|status|run|exec} [prod] | recover prod restore|keep-new"
            echo ""
            echo "  check   Compare local HEAD with the tracked remote branch"
            echo "  status  Show the state of the last/current update run"
            echo "  run     Execute a full update now (maintenance + rebuild + restart)"
            echo "  exec    Executor entry point (used by 'run' and the updater sidecar)"
            echo "  recover Finish a Keycloak upgrade that kept maintenance (restore dump, or keep new)"
            exit 1
            ;;
    esac
}
