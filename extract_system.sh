#!/usr/bin/env bash
#
# extract_system.sh — snapshot the COMPLETE data of a running system (DB + MinIO)
# into a portable folder you can move to the new release/2026.10 system.
#
# NON-DESTRUCTIVE: only reads from the source. Safe to run while the system is up.
#
#   Produces:
#     $OUT_DIR/computor_db.dump      (pg_dump custom format; includes alembic_version)
#     $OUT_DIR/minio/<bucket>/...    (every MinIO bucket, mirrored)
#     $OUT_DIR/MANIFEST.txt
#
# Auth comes from the source system's .env. Connects over the published host
# ports (name-agnostic — works whether the container is docker-postgres-1 or
# computor-postgres-1). Needs Docker; needs NO psql/mc on the host.
#
# Usage (run from the SOURCE repo root, or point ENV_FILE at its .env):
#     bash extract_system.sh
#     ENV_FILE=/path/to/source/.env OUT_DIR=./export_main bash extract_system.sh
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
OUT_DIR="${OUT_DIR:-$ROOT/computor_export}"

[[ -f "$ENV_FILE" ]] || { echo "ERROR: .env not found at $ENV_FILE" >&2; exit 1; }
set -a; source "$ENV_FILE"; set +a

# --- resolve connection params from .env -----------------------------------
PGPORT_VAL="${POSTGRES_EXTERNAL_PORT:-5432}"   # published host port (container itself listens on 5437)
PGUSER_VAL="${POSTGRES_USER:-postgres}"
PGDB_VAL="${POSTGRES_DB:-computor}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD not set in $ENV_FILE}"

MINIO_PORT_VAL="${MINIO_API_PORT:-9000}"
MINIO_USER_VAL="${MINIO_ACCESS_KEY:-${MINIO_ROOT_USER:-minioadmin}}"
MINIO_PASS_VAL="${MINIO_SECRET_KEY:-${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD not set in $ENV_FILE}}"

mkdir -p "$OUT_DIR/minio"

# --- 1) Postgres logical dump ----------------------------------------------
echo ">> [1/2] pg_dump  db='$PGDB_VAL'  127.0.0.1:$PGPORT_VAL ..."
PGPASSWORD="$POSTGRES_PASSWORD" \
docker run --rm --network host -e PGPASSWORD postgres:16 \
  pg_dump -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" -d "$PGDB_VAL" \
          -Fc --no-owner --no-acl \
  > "$OUT_DIR/computor_db.dump"
echo "   -> $OUT_DIR/computor_db.dump ($(du -h "$OUT_DIR/computor_db.dump" | cut -f1))"

# --- 2) MinIO: mirror every bucket -----------------------------------------
# `mc mirror <alias> <dir>` mirrors ALL buckets into <dir>/<bucket>/... (no per-
# bucket enumeration needed, so no awk — the minio/mc image is minimal).
echo ">> [2/2] mirroring ALL MinIO buckets from 127.0.0.1:$MINIO_PORT_VAL (only failures are printed) ..."
# Both credentials go in as environment variables and are only ever expanded
# INSIDE the container's shell: splicing them into the `sh -c` string breaks on
# quotes and `$`, and an MC_HOST_-style URL breaks on the `/ + =` that a
# base64-generated secret routinely contains. Neither value appears in argv.
# NOTE: this mirrors object CONTENT only — bucket policies, versioning and
# lifecycle rules are not carried over.
MINIO_USER="$MINIO_USER_VAL" MINIO_PASS="$MINIO_PASS_VAL" \
docker run --rm --network host -e MINIO_USER -e MINIO_PASS -e MC_CONFIG_DIR=/tmp/mc --user "$(id -u):$(id -g)" \
  -v "$OUT_DIR/minio:/export" --entrypoint sh minio/mc -c '
    set -e
    mc alias set src "http://127.0.0.1:'"$MINIO_PORT_VAL"'" "$MINIO_USER" "$MINIO_PASS" >/dev/null 2>&1
    mc mirror --overwrite src /export 1>/dev/null   # per-object successes go to stdout -> dropped; errors (stderr) still print
  '

# --- manifest ---------------------------------------------------------------
{
  echo "extracted_from_env: $ENV_FILE"
  echo "db: $PGDB_VAL   pg_port: $PGPORT_VAL"
  echo "minio_port: $MINIO_PORT_VAL"
  echo "buckets:"; ls -1 "$OUT_DIR/minio" | sed 's/^/  - /'
  echo "db_dump_bytes: $(stat -c%s "$OUT_DIR/computor_db.dump")"
} > "$OUT_DIR/MANIFEST.txt"

# --- always pack into ONE portable archive; drop the loose dir -------------
ARCHIVE="${OUT_DIR%/}.tar.gz"
echo ">> packing -> $ARCHIVE ..."
tar czf "$ARCHIVE" -C "$(cd "$(dirname "$OUT_DIR")" && pwd)" "$(basename "$OUT_DIR")"
[[ -s "$ARCHIVE" ]] || { echo "ERROR: archive was not created" >&2; exit 1; }
rm -rf "$OUT_DIR"   # keep only the archive (the loose dir was just build staging)
echo ">> Done. Portable snapshot: $ARCHIVE  ($(du -h "$ARCHIVE" | cut -f1))"
echo "   Move it to B, then:  IN_DIR=$ARCHIVE bash load_system.sh"
