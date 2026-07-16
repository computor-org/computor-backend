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
    GIT_TERMINAL_PROMPT=0 git -C "$REPO_ROOT" "${cfg[@]}" fetch "$url" "$branch"
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
build_images() {
    git_build_meta
    ulog "building computor-base (commit ${GIT_COMMIT})"
    (cd "$REPO_ROOT" && docker build -f docker/base/Dockerfile -t computor-base:latest \
        --build-arg GIT_COMMIT="$GIT_COMMIT" --build-arg GIT_BRANCH="$GIT_BRANCH" .) || return 1
    ulog "building computor-testing-runtimes"
    (cd "$REPO_ROOT" && docker build -f docker/testing-runtimes/Dockerfile -t computor-testing-runtimes:latest .) || return 1
    if [ "${CODER_ENABLED:-}" = "true" ]; then
        ulog "building computor-coder-runtime"
        (cd "$REPO_ROOT" && docker build -f docker/coder-runtime/Dockerfile -t computor-coder-runtime:latest .) || return 1
    fi
    ulog "building compose service images"
    compose build || return 1
}

# --- commands ----------------------------------------------------------------

cmd_update_check() {
    ENVIRONMENT="${1:-prod}"
    load_env
    local url="${SYSTEM_REPO_URL:-}" branch="${SYSTEM_REPO_BRANCH:-main}"
    [ -n "$url" ] || die "SYSTEM_REPO_URL is not set in .env"

    local local_head remote_tip
    local_head=$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)
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

    local url="${SYSTEM_REPO_URL:-}" branch="${SYSTEM_REPO_BRANCH:-main}"
    local from_commit to_commit maintenance_entered=0

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
        set_phase rolling_back "Update failed ($1) — restoring ${from_commit}"
        if ! git -C "$REPO_ROOT" checkout -q -B "$branch" "$from_commit"; then
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
    [ -n "$url" ] || fail_update "SYSTEM_REPO_URL is not set in .env"
    git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1 \
        || fail_update "$REPO_ROOT is not a git repository"

    local dirty
    dirty=$(git -C "$REPO_ROOT" status --porcelain --untracked-files=no)
    if [ -n "$dirty" ]; then
        if [ "${UPDATE_GIT_FORCE:-}" = "true" ]; then
            ulog "working tree dirty — discarding local changes (UPDATE_GIT_FORCE=true)"
            git -C "$REPO_ROOT" reset --hard >/dev/null
        else
            fail_update "Working tree has local changes; refusing to update. Commit/stash them or set UPDATE_GIT_FORCE=true in .env. Dirty files: $(echo "$dirty" | awk '{print $2}' | tr '\n' ' ')"
        fi
    fi

    from_commit=$(git -C "$REPO_ROOT" rev-parse HEAD)
    set_update_state from_commit "$from_commit"

    # 2. fetch ------------------------------------------------------------------
    set_phase checking "Fetching ${branch} from remote"
    git_fetch_tracked "$url" "$branch" || fail_update "git fetch from configured SYSTEM_REPO_URL failed"
    to_commit=$(git -C "$REPO_ROOT" rev-parse FETCH_HEAD)
    set_update_state to_commit "$to_commit"

    if [ "$to_commit" = "$from_commit" ]; then
        finish_update success "Already up to date (${from_commit})."
    fi

    # 3. checkout ---------------------------------------------------------------
    set_phase checking_out "Checking out ${to_commit}"
    git -C "$REPO_ROOT" checkout -q -B "$branch" FETCH_HEAD \
        || fail_update "git checkout of ${to_commit} failed"

    # New-tree preflight: catches broken compose interpolation (e.g. a new :?
    # variable missing from .env) BEFORE any downtime.
    if ! compose config -q; then
        git -C "$REPO_ROOT" checkout -q -B "$branch" "$from_commit"
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
    ensure_maintenance_page
    activate_traefik_maintenance
    local service
    for service in $(get_stoppable_services); do
        compose stop "$service" >/dev/null 2>&1 && ulog "stopped: $service" || true
    done

    # 6. start ---------------------------------------------------------------------
    set_phase starting "Starting services on ${to_commit}"
    compose up -d || do_rollback "'compose up' failed"

    # 7. health check ----------------------------------------------------------------
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
        *)
            echo "Usage: $0 update {check|status|run|exec} [prod]"
            echo ""
            echo "  check   Compare local HEAD with the tracked remote branch"
            echo "  status  Show the state of the last/current update run"
            echo "  run     Execute a full update now (maintenance + rebuild + restart)"
            echo "  exec    Executor entry point (used by 'run' and the updater sidecar)"
            exit 1
            ;;
    esac
}
