#!/usr/bin/env bash
#
# load_system.sh — load a snapshot produced by extract_system.sh into the NEW
# (release/2026.10) system, MIGRATE it to the release schema, and ADOPT the legacy
# per-ORGANIZATION GitLab config into the new per-COURSE git model.
#
# Runs three stages, each independently skippable:
#   [1] RESTORE — DROP+recreate the target DB from the dump, mirror MinIO buckets.
#                 Restores at main's schema (alembic_version = cc1d2e3f4a5b).
#   [2] MIGRATE — `alembic upgrade head`: replays the release migrations, incl.
#                 creating the git_server / course_git_binding tables.
#   [3] ADOPT   — for every course carrying legacy `properties.gitlab`, register a
#                 gitlab `git_server` and create a `course_git_binding` pointing at
#                 the EXISTING student-template, copying the group token from the
#                 course's ORGANIZATION (`organization.properties.gitlab.token`) onto
#                 the binding. The token is decrypted with the LEGACY TOKEN_SECRET and
#                 re-encrypted with THIS system's TOKEN_SECRET (keycove is wire-
#                 compatible), so it works even when the two secrets differ.
#                 DRY-RUN by default — set ADOPT_APPLY=1 to write. Adoptive only:
#                 it NEVER calls GitLab, it just records where repos already live.
#                 Assumes all legacy git was managed + gitlab (no forgejo).
#
# DESTRUCTIVE to the TARGET: stage 1 DROPs and recreates the target database.
# Auth from the TARGET system's .env. Restore uses Docker over published host ports;
# migrate/adopt use the repo-root .venv. Needs NO psql/mc on the host.
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
#   SKIP_MIGRATE=1        skip stage 2 (alembic upgrade head)
#   SKIP_ADOPT=1          skip stage 3 (git adoption)
#   ADOPT_APPLY=1         stage 3 writes bindings (default: dry-run, rolled back)
#   LEGACY_TOKEN_SECRET=  the SOURCE system's TOKEN_SECRET (to decrypt migrated
#                         tokens). If unset you are prompted; blank = same as target's.
#   GITLAB_BASE_URL=      override the git_server base_url (else from org properties.gitlab.url)
#   GITLAB_NAME=          display name for the registered git_server
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
IN_DIR="${IN_DIR:-$ROOT/computor_export.tar.gz}"

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
  if [[ "${FORCE:-0}" != "1" ]]; then
    read -r -p "Proceed? type 'yes': " ans; [[ "$ans" == "yes" ]] || { echo "aborted"; exit 1; }
  fi

  echo ">> [1/3] restoring database ..."
  PGPASSWORD="$POSTGRES_PASSWORD" docker run --rm --network host -e PGPASSWORD postgres:16 \
    dropdb   -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" --force --if-exists "$PGDB_VAL"
  PGPASSWORD="$POSTGRES_PASSWORD" docker run --rm --network host -e PGPASSWORD postgres:16 \
    createdb -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" "$PGDB_VAL"
  PGPASSWORD="$POSTGRES_PASSWORD" docker run --rm -i --network host -e PGPASSWORD postgres:16 \
    pg_restore -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" -d "$PGDB_VAL" --no-owner --no-acl \
    < "$IN_DIR/computor_db.dump"
  echo "   restored (alembic_version below should be main's head cc1d2e3f4a5b):"
  PGPASSWORD="$POSTGRES_PASSWORD" docker run --rm --network host -e PGPASSWORD postgres:16 \
    psql -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" -d "$PGDB_VAL" -tAc "SELECT version_num FROM alembic_version" \
    | sed 's/^/     /'

  echo ">> restoring MinIO buckets ..."
  BUCKETS=""
  for d in "$IN_DIR"/minio/*/; do [[ -d "$d" ]] || continue; BUCKETS="$BUCKETS $(basename "$d")"; done
  if [[ -z "${BUCKETS// }" ]]; then
    echo "   (no buckets in $IN_DIR/minio — skipping)"
  else
    MINIO_PASS="$MINIO_PASS_VAL" BUCKETS="$BUCKETS" \
    docker run --rm --network host -e MINIO_PASS -e BUCKETS \
      -v "$IN_DIR/minio:/import" --entrypoint sh minio/mc -c '
        set -e
        mc alias set dst "http://127.0.0.1:'"$MINIO_PORT_VAL"'" "'"$MINIO_USER_VAL"'" "$MINIO_PASS" >/dev/null 2>&1
        for b in $BUCKETS; do
          echo "   bucket: $b"
          mc mb --ignore-existing "dst/$b" >/dev/null
          mc mirror --overwrite "/import/$b" "dst/$b" >/dev/null
        done
      '
  fi
else
  echo ">> [1/3] SKIP_RESTORE=1 -> skipping DB/MinIO restore"
fi

# ===========================================================================
# [2] MIGRATE — replay release migrations onto the restored schema
# ===========================================================================
if [[ "${SKIP_MIGRATE:-0}" != "1" ]]; then
  echo ">> [2/3] migrating target to release head (alembic upgrade head) ..."
  ALEMBIC_BIN="$ROOT/.venv/bin/alembic"; [[ -x "$ALEMBIC_BIN" ]] || ALEMBIC_BIN="alembic"
  ( cd "$ROOT/computor-backend/src" \
      && export PYTHONPATH="$PWD:${PYTHONPATH:-}" \
      && cd computor_backend \
      && "$ALEMBIC_BIN" upgrade head )
  echo "   head now:"
  PGPASSWORD="$POSTGRES_PASSWORD" docker run --rm --network host -e PGPASSWORD postgres:16 \
    psql -h 127.0.0.1 -p "$PGPORT_VAL" -U "$PGUSER_VAL" -d "$PGDB_VAL" -tAc "SELECT version_num FROM alembic_version" \
    | sed 's/^/     /'
else
  echo ">> [2/3] SKIP_MIGRATE=1 -> skipping migration"
fi

# ===========================================================================
# [3] ADOPT — legacy org GitLab config -> per-course git bindings (token bridged)
# ===========================================================================
if [[ "${SKIP_ADOPT:-0}" != "1" ]]; then
  echo ">> [3/3] adopting legacy GitLab config into course_git_binding ..."
  PY_BIN="$ROOT/.venv/bin/python"; [[ -x "$PY_BIN" ]] || PY_BIN="python3"

  if [[ -z "${LEGACY_TOKEN_SECRET:-}" && -t 0 && "${FORCE:-0}" != "1" ]]; then
    read -r -s -p "   Legacy TOKEN_SECRET to decrypt migrated tokens (blank = same as target's): " LEGACY_TOKEN_SECRET || true
    echo
  fi
  export LEGACY_TOKEN_SECRET="${LEGACY_TOKEN_SECRET:-${TOKEN_SECRET:-}}"
  export PGPORT_VAL PGUSER_VAL PGDB_VAL
  export ADOPT_APPLY="${ADOPT_APPLY:-0}"
  export GITLAB_BASE_URL="${GITLAB_BASE_URL:-}"
  export GITLAB_NAME="${GITLAB_NAME:-}"

  "$PY_BIN" - <<'PYEOF'
import os, sys, json
from sqlalchemy import create_engine, text
try:
    from keycove import encrypt, decrypt   # same primitive computor_types.encryption uses
except Exception as e:  # pragma: no cover
    sys.exit("   !! keycove not importable (%s); cannot bridge tokens" % e)

APPLY      = os.environ.get("ADOPT_APPLY") == "1"
NEW_SECRET = os.environ.get("TOKEN_SECRET") or ""
LEG_SECRET = os.environ.get("LEGACY_TOKEN_SECRET") or NEW_SECRET
BASE_OVER  = (os.environ.get("GITLAB_BASE_URL") or "").rstrip("/") or None
NAME_OVER  = os.environ.get("GITLAB_NAME") or None
if not NEW_SECRET:
    sys.exit("   !! TOKEN_SECRET not set in target .env; cannot re-encrypt tokens")

eng = create_engine("postgresql+psycopg2://%s:%s@127.0.0.1:%s/%s" % (
    os.environ["PGUSER_VAL"], os.environ["POSTGRES_PASSWORD"],
    os.environ["PGPORT_VAL"], os.environ["PGDB_VAL"]))

def as_dict(v):
    if v is None: return {}
    if isinstance(v, dict): return v
    try: return json.loads(v)
    except Exception: return {}

def extract_template(cg, base_url):
    """Return (template_repo, template_url) from a legacy course gitlab blob,
    handling both the flat (template_path) and nested (projects.student_template)
    shapes."""
    tp = cg.get("template_path") or cg.get("full_path")
    if tp:
        return tp, (cg.get("template_url") or (("%s/%s.git" % (base_url, tp)) if base_url else None))
    projects = cg.get("projects") or {}
    st = projects.get("student_template") or projects.get("student-template") or projects.get("template") or {}
    fp = st.get("full_path") if isinstance(st, dict) else None
    if not fp and cg.get("full_path"):
        fp = "%s/student-template" % cg["full_path"]
    if not fp:
        return None, None
    tu = (st.get("http_url_to_repo") if isinstance(st, dict) else None) or (("%s/%s.git" % (base_url, fp)) if base_url else None)
    return fp, tu

print("\n   === adoption %s | legacy-secret=%s ===" % (
    "APPLY" if APPLY else "DRY-RUN",
    "custom" if LEG_SECRET != NEW_SECRET else "same-as-target"))

conn = eng.connect()
trans = conn.begin()
servers = {}

def get_server(base_url):
    if base_url in servers:
        return servers[base_url]
    row = conn.execute(text("SELECT id FROM git_server WHERE type='gitlab' AND base_url=:u"),
                       {"u": base_url}).first()
    if row:
        servers[base_url] = row[0]
        print("     git_server reuse: %s (%s)" % (base_url, str(row[0])[:8]))
        return row[0]
    name = NAME_OVER or ("GitLab (%s)" % base_url)
    nid = conn.execute(text(
        "INSERT INTO git_server (type, base_url, name, managed) "
        "VALUES ('gitlab', :u, :n, false) RETURNING id"), {"u": base_url, "n": name}).scalar()
    servers[base_url] = nid
    print("     git_server CREATE: %s (%s) name=%r" % (base_url, str(nid)[:8], name))
    return nid

rows = conn.execute(text("""
    SELECT c.id, c.title, c.properties->'gitlab', o.title, o.properties->'gitlab'
    FROM course c JOIN organization o ON o.id = c.organization_id
    WHERE c.properties ? 'gitlab'
    ORDER BY o.title, c.title
""")).all()
print("     %d course(s) carry properties.gitlab\n" % len(rows))

created = existing = skipped = 0
errors = []
for cid, ctitle, cg_raw, otitle, og_raw in rows:
    cg = as_dict(cg_raw); og = as_dict(og_raw)
    print("   - %s  (org: %s)" % (ctitle, otitle))
    if conn.execute(text("SELECT 1 FROM course_git_binding WHERE course_id=:c"), {"c": cid}).first():
        print("       -> SKIP (already bound)"); existing += 1; continue
    base_url = BASE_OVER or ((og.get("url") or "").rstrip("/") or None)
    if not base_url:
        print("       -> SKIP (no gitlab base_url on org; pass GITLAB_BASE_URL= to override)"); skipped += 1; continue
    tpl_repo, tpl_url = extract_template(cg, base_url)
    if not tpl_repo:
        print("       -> SKIP (no student-template found; gitlab keys=%s)" % list(cg.keys())); skipped += 1; continue
    tok_ct = None
    enc = og.get("token")
    if enc:
        try:
            pt = decrypt(enc, LEG_SECRET)
            if not isinstance(pt, str) or not pt.strip():
                raise ValueError("decrypted to empty string")
            tok_ct = encrypt(pt, NEW_SECRET)
            warn = "" if pt.startswith("glpat-") else "  (WARN: plaintext is not a glpat- token)"
            print("       token: org token decrypted OK -> re-encrypted%s" % warn)
        except Exception as e:
            print("       -> ERROR decrypting org token: %s  (wrong LEGACY_TOKEN_SECRET?)" % e)
            errors.append(ctitle); skipped += 1; continue
    else:
        print("       token: NONE on org.properties.gitlab (binding will have no credential)")
    pgid = cg.get("parent_group_id") or cg.get("parent") or cg.get("parent_id")
    props = {"gitlab": dict(cg)}
    if pgid is not None:
        props["gitlab"]["parent_group_id"] = pgid
    srv = get_server(base_url)
    print("       -> BIND server=%s template_repo=%s parent_group_id=%s token=%s modes=[managed]" % (
        base_url, tpl_repo, pgid, "set" if tok_ct else "none"))
    created += 1
    if APPLY:
        conn.execute(text("""
            INSERT INTO course_git_binding
              (course_id, delivery, git_server_id, template_repo, template_url,
               default_branch, token, student_repo_modes, properties)
            VALUES (:c, 'git', :srv, :tr, :tu, 'main', :tok,
                    CAST(:modes AS jsonb), CAST(:props AS jsonb))
        """), {"c": cid, "srv": srv, "tr": tpl_repo, "tu": tpl_url, "tok": tok_ct,
               "modes": json.dumps(["managed"]), "props": json.dumps(props)})

if errors and APPLY:
    trans.rollback()
    sys.exit("\n   !! %d course(s) failed token-decrypt -> NOTHING written. Fix "
             "LEGACY_TOKEN_SECRET and re-run: SKIP_RESTORE=1 SKIP_MIGRATE=1 ADOPT_APPLY=1 bash load_system.sh"
             % len(errors))

if APPLY:
    trans.commit()
    print("\n   === APPLIED: %d created, %d already bound, %d skipped ===" % (created, existing, skipped))
else:
    trans.rollback()
    print("\n   === DRY-RUN: would create %d, %d already bound, %d skipped. "
          "Re-run with ADOPT_APPLY=1 to write. ===" % (created, existing, skipped))
    if errors:
        print("   (%d course(s) would fail token-decrypt with the current LEGACY_TOKEN_SECRET)" % len(errors))
PYEOF
else
  echo ">> [3/3] SKIP_ADOPT=1 -> skipping git adoption"
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
