#!/usr/bin/env bash
#
# adopt_git.sh — adopt a legacy system's org-level GitLab configuration into the
# per-course git model, entirely through the running backend container.
#
# The work is done by computor-backend/src/computor_backend/scripts/adopt_legacy_git.py,
# which is PIPED INTO the container on stdin. That means the version in this
# working copy runs against whatever image is deployed — no rebuild, no redeploy.
# load_system.sh runs the very same module on the host; there is one
# implementation of the mapping, not two.
#
# It never contacts GitLab unless you pass --resolve-ids, and even then only
# issues read-only lookups. It creates, renames and deletes nothing on the git
# server; it records where repositories already live.
#
# ORDER MATTERS. `alembic upgrade head` DESTROYS the organization's GitLab token
# and url (migration b1c2d3e4f5a6 moves them into a git_provider table, which
# f0a1b2c3d4e5 then drops). Stash them first, or there is nothing left to bridge:
#
#     ./adopt_git.sh --preflight                        # on the restored DB
#     ./adopt_git.sh --stash-org-git --apply            # BEFORE migrating
#     ./adopt_git.sh --migrate                          # alembic upgrade head
#     ./adopt_git.sh <LEGACY_TOKEN_SECRET>              # dry-run the adoption
#     ./adopt_git.sh <LEGACY_TOKEN_SECRET> --apply      # write it
#
# NOTE: this script is DRY-RUN by default (it used to apply by default). Pass
# --apply to write, matching load_system.sh so one habit works for both.
#
# Env knobs:
#   CONTAINER=name   backend container (default: auto-detected from compose labels)
#   ENV_FILE=path    .env location (default: ./.env in the current directory)
#   Anything else is forwarded to the module — see `./adopt_git.sh --help`.
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADOPT_PY="$ROOT/computor-backend/src/computor_backend/scripts/adopt_legacy_git.py"
[[ -f "$ADOPT_PY" ]] || { echo "ERROR: adoption module not found at $ADOPT_PY" >&2; exit 1; }

# A bare first argument is the legacy TOKEN_SECRET (backwards compatible), but
# prefer the environment: argv is visible in `ps` and in shell history.
args=()
for arg in "$@"; do
  case "$arg" in
    -*) args+=("$arg") ;;
    *)  LEGACY_TOKEN_SECRET="$arg" ;;
  esac
done

ENV_FILE="${ENV_FILE:-$PWD/.env}"
[[ -f "$ENV_FILE" ]] || { echo "ERROR: .env not found at $ENV_FILE (run from the dir containing it)" >&2; exit 1; }
set -a; source "$ENV_FILE"; set +a
: "${TOKEN_SECRET:?TOKEN_SECRET not set in $ENV_FILE — needed to re-encrypt tokens}"
export TOKEN_SECRET
export LEGACY_TOKEN_SECRET="${LEGACY_TOKEN_SECRET:-$TOKEN_SECRET}"

# --- locate the backend container ------------------------------------------
# The compose service has no container_name, so the real name is the
# project-prefixed, index-suffixed one (computor-uvicorn-1). Resolve it by label
# rather than guessing.
if [[ -z "${CONTAINER:-}" ]]; then
  CONTAINER="$(docker ps --filter 'label=com.docker.compose.service=uvicorn' \
                         --format '{{.Names}}' | head -1)"
fi
[[ -n "${CONTAINER:-}" ]] || {
  echo "ERROR: could not find the running backend container." >&2
  echo "       Start the stack, or set CONTAINER=<name> explicitly." >&2
  exit 1
}
[[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)" == "true" ]] || {
  echo "ERROR: container '$CONTAINER' is not running" >&2; exit 1; }

# --- optional: run the migration in the container ---------------------------
migrate=0
filtered=()
for arg in ${args[@]+"${args[@]}"}; do
  [[ -z "$arg" ]] && continue
  if [[ "$arg" == "--migrate" ]]; then migrate=1; else filtered+=("$arg"); fi
done

echo ">> container:  $CONTAINER"
echo ">> env file:   $ENV_FILE"
echo ">> legacy secret: $([[ "$LEGACY_TOKEN_SECRET" != "$TOKEN_SECRET" ]] && echo custom || echo same-as-target)"

if [[ "$migrate" == "1" ]]; then
  echo ">> alembic upgrade head ..."
  docker exec "$CONTAINER" sh -c 'cd computor-backend/src/computor_backend && alembic upgrade head'
  docker exec "$CONTAINER" sh -c 'cd computor-backend/src/computor_backend && alembic current' 2>/dev/null | sed 's/^/     now at: /'
  [[ ${#filtered[@]} -eq 0 ]] && exit 0
fi

# --- run the adoption module inside the container ---------------------------
# `-e NAME` (no `=value`) takes the value from THIS shell's environment, so the
# secrets never appear in the container's argv or in `docker inspect`.
docker exec -i \
  -e TOKEN_SECRET -e LEGACY_TOKEN_SECRET -e ADOPT_GITLAB_TOKEN \
  -e GITLAB_BASE_URL -e GITLAB_NAME \
  "$CONTAINER" python3 - ${filtered[@]+"${filtered[@]}"} < "$ADOPT_PY"

# --- restart so the API serves the adopted data -----------------------------
for arg in ${filtered[@]+"${filtered[@]}"}; do
  if [[ "$arg" == "--apply" && "${SKIP_RESTART:-0}" != "1" ]]; then
    echo ">> restarting $CONTAINER ..."
    docker restart "$CONTAINER" >/dev/null
    worker="$(docker ps --filter 'label=com.docker.compose.service=temporal-worker' --format '{{.Names}}' | head -1)"
    if [[ -n "$worker" ]]; then
      echo ">> restarting $worker ..."
      docker restart "$worker" >/dev/null
    else
      echo "   (no temporal-worker container found — restart your workers manually)"
    fi
    break
  fi
done

echo ">> Done."
