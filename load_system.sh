#!/usr/bin/env bash
#
# load_system.sh — load a snapshot produced by extract_system.sh into the NEW
# (release/2026.10) system, MIGRATE it to the release schema, and ADOPT the legacy
# per-ORGANIZATION GitLab config into the new per-COURSE git model.
#
# Runs four stages, each independently skippable:
#   [1] RESTORE — DROP+recreate the target DB from the dump, mirror MinIO buckets.
#                 Restores at main's schema (alembic_version = cc1d2e3f4a5b).
#   [2] STASH   — copy organization.properties.gitlab aside BEFORE migrating.
#                 THIS MUST HAPPEN FIRST: `alembic upgrade head` destroys the org
#                 GitLab token and url (b1c2d3e4f5a6 moves them into a
#                 git_provider table; f0a1b2c3d4e5 then drops that table), so
#                 without the stash there is no credential left to bridge.
#   [3] MIGRATE — `alembic upgrade head`: replays the release migrations, incl.
#                 creating the git_server / course_git_binding tables.
#   [4] ADOPT   — for every course carrying legacy `properties.gitlab`, register a
#                 gitlab `git_server` and write a `course_git_binding` that maps the
#                 legacy repository names onto the new model:
#
#                     student-template -> template_repo / template_path
#                     assignments      -> reference_path
#
#                 plus the students/course/parent group ids, and the existing
#                 student repositories as course_member_repository rows. The org
#                 token is decrypted with the LEGACY TOKEN_SECRET and re-encrypted
#                 with THIS system's (keycove is wire-compatible), so it works even
#                 when the two secrets differ.
#
#                 DRY-RUN by default — set ADOPT_APPLY=1 to write. It contacts
#                 GitLab only with ADOPT_RESOLVE_IDS=1, and then only to READ.
#                 Nothing is ever created, renamed or deleted on the git server.
#
# The adoption itself lives in
#   computor-backend/src/computor_backend/scripts/adopt_legacy_git.py
# and is the same module adopt_git.sh pipes into the backend container, so the
# mapping has exactly one implementation. Run it directly for --preflight,
# --repair, or anything else this wrapper does not expose.
#
# DESTRUCTIVE to the TARGET: stage 1 DROPs and recreates the target database.
# Auth from the TARGET system's .env. Restore uses Docker over published host ports;
# stash/migrate/adopt use the repo-root .venv. Needs NO psql/mc on the host.
#
# Usage (from the TARGET repo root):
#   IN_DIR=./computor_export.tar.gz bash load_system.sh                 # restore+migrate+adopt(dry-run)
#   IN_DIR=./computor_export.tar.gz FORCE=1 bash load_system.sh          # skip the drop prompt
#   ADOPT_APPLY=1 LEGACY_TOKEN_SECRET=<legacy> IN_DIR=... bash load_system.sh   # write bindings
#   SKIP_RESTORE=1 SKIP_MIGRATE=1 ADOPT_APPLY=1 LEGACY_TOKEN_SECRET=<legacy> bash load_system.sh  # re-run adopt only
#
# Env knobs:
#   FORCE=1               skip the "drop the DB?" confirmation (and the secret prompt)
#   SKIP_RESTORE=1        skip stage 1 (DB/MinIO restore)
#   SKIP_MIGRATE=1        skip stages 2+3 (stash + alembic upgrade head)
#   SKIP_ADOPT=1          skip stages 2+4 (stash + git adoption)
#   ADOPT_APPLY=1         stage 4 writes bindings (default: dry-run, rolled back)
#   ADOPT_RESOLVE_IDS=1   resolve GitLab project ids with READ-ONLY API calls, so
#                         managed student provisioning works for adopted courses
#   LEGACY_TOKEN_SECRET=  the SOURCE system's TOKEN_SECRET (to decrypt migrated
#                         tokens). If unset you are prompted; blank = same as target's.
#   GITLAB_BASE_URL=      override the git_server base_url (else from course/org properties)
#   GITLAB_NAME=          display name for the registered git_server
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
IN_DIR="${IN_DIR:-$ROOT/computor_export.tar.gz}"

# The legacy system's single alembic head. A dump at any other revision is not
# the thing this script knows how to migrate.
LEGACY_HEAD="cc1d2e3f4a5b"

[[ -f "$ENV_FILE" ]] || { echo "ERROR: target .env not found at $ENV_FILE" >&2; exit 1; }
set -a; source "$ENV_FILE"; set +a

PGPORT_VAL="${POSTGRES_EXTERNAL_PORT:-5432}"   # published host port (container listens on 5437)
PGUSER_VAL="${POSTGRES_USER:-postgres}"
PGDB_VAL="${POSTGRES_DB:-computor}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD not set in $ENV_FILE}"

MINIO_PORT_VAL="${MINIO_API_PORT:-9000}"
MINIO_USER_VAL="${MINIO_ACCESS_KEY:-${MINIO_ROOT_USER:-minioadmin}}"
MINIO_PASS_VAL="${MINIO_SECRET_KEY:-${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD not set in $ENV_FILE}}"

CLEANUP_DIR=""
trap '[[ -n "$CLEANUP_DIR" ]] && rm -rf "$CLEANUP_DIR"' EXIT

# ===========================================================================
# [1] RESTORE — drop+recreate DB from dump, mirror MinIO buckets
# ===========================================================================
if [[ "${SKIP_RESTORE:-0}" != "1" ]]; then
  # Accept a .tar.gz/.tgz produced by extract_system.sh — unpack to a temp dir.
  if [[ -f "$IN_DIR" && "$IN_DIR" =~ \.(tar\.gz|tgz)$ ]]; then
    CLEANUP_DIR="$(mktemp -d)"
    echo ">> unpacking $IN_DIR ..."
    tar xzf "$IN_DIR" -C "$CLEANUP_DIR"
    if [[ -f "$CLEANUP_DIR/computor_db.dump" ]]; then
      IN_DIR="$CLEANUP_DIR"
    else
      IN_DIR="$(find "$CLEANUP_DIR" -maxdepth 2 -name computor_db.dump -printf '%h\n' | head -1)"
    fi
  fi
  [[ -n "$IN_DIR" && -f "$IN_DIR/computor_db.dump" ]] || { echo "ERROR: computor_db.dump not found (IN_DIR=$IN_DIR)" >&2; exit 1; }

  echo "TARGET: db '$PGDB_VAL' @ 127.0.0.1:$PGPORT_VAL   |   MinIO @ 127.0.0.1:$MINIO_PORT_VAL"
  echo "SOURCE: $IN_DIR"
  echo "!! This DROPS and recreates the target database '$PGDB_VAL'."

  # `dropdb --force` terminates existing connections, but the API and the
  # Temporal workers reconnect within seconds — against a half-restored
  # database, where they can auto-provision users and fail migrations on locks.
  # Refuse to start while anything else is connected.
  others="$(PGPASSWORD="$POSTGRES_PASSWORD" docker run --rm --network host -e PGPASSWORD postgres:16 \
    psql -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" -d postgres -tAc \
    "SELECT count(*) FROM pg_stat_activity WHERE datname = '$PGDB_VAL' AND pid <> pg_backend_pid()" 2>/dev/null || echo 0)"
  if [[ "${others:-0}" -gt 0 ]]; then
    echo "ERROR: $others other connection(s) to '$PGDB_VAL' are open." >&2
    echo "       Stop the API and the Temporal workers first (./api.sh stop, ./computor.sh down)," >&2
    echo "       or they will reconnect to a half-restored database." >&2
    exit 1
  fi

  if [[ "${FORCE:-0}" != "1" ]]; then
    read -r -p "Proceed? type 'yes': " ans; [[ "$ans" == "yes" ]] || { echo "aborted"; exit 1; }
  fi

  echo ">> [1/4] restoring database ..."
  PGPASSWORD="$POSTGRES_PASSWORD" docker run --rm --network host -e PGPASSWORD postgres:16 \
    dropdb   -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" --force --if-exists "$PGDB_VAL"
  PGPASSWORD="$POSTGRES_PASSWORD" docker run --rm --network host -e PGPASSWORD postgres:16 \
    createdb -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" "$PGDB_VAL"
  PGPASSWORD="$POSTGRES_PASSWORD" docker run --rm -i --network host -e PGPASSWORD postgres:16 \
    pg_restore -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" -d "$PGDB_VAL" --no-owner --no-acl \
    < "$IN_DIR/computor_db.dump"
  # Assert rather than print: the stages below assume the legacy schema, and
  # their behaviour on an unexpected revision is undefined.
  restored_head="$(PGPASSWORD="$POSTGRES_PASSWORD" docker run --rm --network host -e PGPASSWORD postgres:16 \
    psql -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" -d "$PGDB_VAL" -tAc "SELECT version_num FROM alembic_version")"
  echo "   restored at alembic head: ${restored_head:-<none>}"
  if [[ "$restored_head" != "$LEGACY_HEAD" ]]; then
    echo "ERROR: expected the legacy head $LEGACY_HEAD, got '${restored_head:-<none>}'." >&2
    echo "       This dump is not from the legacy system this script migrates." >&2
    echo "       Set SKIP_RESTORE=1 to skip stage 1 if you know what you are doing." >&2
    exit 1
  fi

  echo ">> restoring MinIO buckets ..."
  BUCKETS=""
  for d in "$IN_DIR"/minio/*/; do [[ -d "$d" ]] || continue; BUCKETS="$BUCKETS $(basename "$d")"; done
  if [[ -z "${BUCKETS// }" ]]; then
    echo "   (no buckets in $IN_DIR/minio — skipping)"
  else
    MINIO_USER="$MINIO_USER_VAL" MINIO_PASS="$MINIO_PASS_VAL" BUCKETS="$BUCKETS" \
    docker run --rm --network host -e MINIO_USER -e MINIO_PASS -e BUCKETS \
      -v "$IN_DIR/minio:/import" --entrypoint sh minio/mc -c '
        set -e
        mc alias set dst "http://127.0.0.1:'"$MINIO_PORT_VAL"'" "$MINIO_USER" "$MINIO_PASS" >/dev/null 2>&1
        for b in $BUCKETS; do
          echo "   bucket: $b"
          mc mb --ignore-existing "dst/$b" >/dev/null
          mc mirror --overwrite "/import/$b" "dst/$b" >/dev/null
        done
      '
  fi
else
  echo ">> [1/4] SKIP_RESTORE=1 -> skipping DB/MinIO restore"
fi

# ===========================================================================
# [2] STASH — preserve the org GitLab credential BEFORE migrating
#
# `alembic upgrade head` destroys it: migration b1c2d3e4f5a6 moves
# organization.properties.gitlab.{url,token} into a git_provider table and
# strips them from the JSONB, and f0a1b2c3d4e5 then drops that table. Without
# this step there is no token left to bridge onto the course bindings.
# ===========================================================================
ADOPT_PY="$ROOT/computor-backend/src/computor_backend/scripts/adopt_legacy_git.py"
PY_BIN="$ROOT/.venv/bin/python"; [[ -x "$PY_BIN" ]] || PY_BIN="python3"
export PYTHONPATH="$ROOT/computor-backend/src:$ROOT/computor-types/src${PYTHONPATH:+:$PYTHONPATH}"
# One address for every stage: stage 3 below reads these too, and alembic builds
# its own URL from POSTGRES_HOST/POSTGRES_PORT rather than the published port.
export POSTGRES_HOST=127.0.0.1
export POSTGRES_PORT="$PGPORT_VAL"
export POSTGRES_USER="$PGUSER_VAL"
export POSTGRES_DB="$PGDB_VAL"

if [[ "${SKIP_ADOPT:-0}" != "1" && "${SKIP_MIGRATE:-0}" != "1" ]]; then
  echo ">> [2/4] stashing the organization GitLab credential (pre-migration) ..."
  "$PY_BIN" "$ADOPT_PY" --stash-org-git --apply
fi

# ===========================================================================
# [3] MIGRATE — replay release migrations onto the restored schema
# ===========================================================================
if [[ "${SKIP_MIGRATE:-0}" != "1" ]]; then
  echo ">> [3/4] migrating target to release head (alembic upgrade head) ..."
  ALEMBIC_BIN="$ROOT/.venv/bin/alembic"; [[ -x "$ALEMBIC_BIN" ]] || ALEMBIC_BIN="alembic"
  ( cd "$ROOT/computor-backend/src" \
      && cd computor_backend \
      && "$ALEMBIC_BIN" upgrade head )
  echo "   head now:"
  PGPASSWORD="$POSTGRES_PASSWORD" docker run --rm --network host -e PGPASSWORD postgres:16 \
    psql -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" -d "$PGDB_VAL" -tAc "SELECT version_num FROM alembic_version" \
    | sed 's/^/     /'
else
  echo ">> [3/4] SKIP_MIGRATE=1 -> skipping migration"
fi

# ===========================================================================
# [4] ADOPT — legacy org GitLab config -> per-course git bindings
#
# Runs the SAME module adopt_git.sh pipes into the backend container, so the
# mapping (student-template -> template, assignments -> reference) has exactly
# one implementation.
# ===========================================================================
if [[ "${SKIP_ADOPT:-0}" != "1" ]]; then
  echo ">> [4/4] adopting legacy GitLab config into course_git_binding ..."

  if [[ -z "${LEGACY_TOKEN_SECRET:-}" && -t 0 && "${FORCE:-0}" != "1" ]]; then
    read -r -s -p "   Legacy TOKEN_SECRET to decrypt migrated tokens (blank = same as target's): " LEGACY_TOKEN_SECRET || true
    echo
  fi
  # Defaulting to the target's secret is right for a same-system re-run and
  # wrong for an actual migration, where it produces a decrypt failure that
  # looks like a corrupt token. Non-interactively, make the choice explicit.
  if [[ -z "${LEGACY_TOKEN_SECRET:-}" && "${ADOPT_APPLY:-0}" == "1" ]]; then
    echo "ERROR: LEGACY_TOKEN_SECRET is not set and there is no terminal to ask." >&2
    echo "       Set it to the SOURCE system's TOKEN_SECRET, or set it equal to this" >&2
    echo "       system's if the snapshot was taken from this same system." >&2
    exit 1
  fi
  export LEGACY_TOKEN_SECRET="${LEGACY_TOKEN_SECRET:-${TOKEN_SECRET:-}}"

  adopt_args=()
  [[ "${ADOPT_APPLY:-0}" == "1" ]] && adopt_args+=(--apply)
  [[ "${ADOPT_RESOLVE_IDS:-0}" == "1" ]] && adopt_args+=(--resolve-ids)
  [[ -n "${GITLAB_BASE_URL:-}" ]] && adopt_args+=(--gitlab-base-url "$GITLAB_BASE_URL")
  [[ -n "${GITLAB_NAME:-}" ]] && adopt_args+=(--gitlab-name "$GITLAB_NAME")

  "$PY_BIN" "$ADOPT_PY" ${adopt_args[@]+"${adopt_args[@]}"}
else
  echo ">> [4/4] SKIP_ADOPT=1 -> skipping git adoption"
fi


# --- summary ----------------------------------------------------------------
r_stat="yes"; if [[ "${SKIP_RESTORE:-0}" == "1" ]]; then r_stat="skipped"; fi
m_stat="yes"; if [[ "${SKIP_MIGRATE:-0}" == "1" ]]; then m_stat="skipped"; fi
if [[ "${SKIP_ADOPT:-0}" == "1" ]]; then a_stat="skipped";
elif [[ "${ADOPT_APPLY:-0}" == "1" ]]; then a_stat="applied";
else a_stat="dry-run"; fi
echo
echo ">> Done.  restore=$r_stat  migrate=$m_stat  adopt=$a_stat"
if [[ "$a_stat" == "dry-run" ]]; then
  echo "   Review the adoption plan above, then apply with:"
  echo "     SKIP_RESTORE=1 SKIP_MIGRATE=1 ADOPT_APPLY=1 LEGACY_TOKEN_SECRET=<legacy> bash load_system.sh"
fi
