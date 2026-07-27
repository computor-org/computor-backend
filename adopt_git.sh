#!/usr/bin/env bash
#
# adopt_git.sh — finish a legacy import ENTIRELY through the running backend
# container. Does two things, both via `docker exec` into `computor-uvicorn`
# (which has Python 3.10 + alembic + sqlalchemy + keycove + the models, and
# reaches the same postgres):
#
#   [1] MIGRATE — `alembic upgrade head` (idempotent; brings the restored DB to
#                 the release schema, incl. git_server / course_git_binding).
#   [2] ADOPT   — for every course carrying legacy `properties.gitlab`, register a
#                 gitlab `git_server` and create a `course_git_binding` pointing at
#                 the EXISTING student-template, bridging the org's group token
#                 from the LEGACY secret to THIS system's TOKEN_SECRET.
#
# It NEVER contacts GitLab and cannot alter/destroy any GitLab repo or group —
# it only records where repos already live. A wrong legacy token makes the whole
# adoption roll back (nothing written), so re-running is safe and idempotent
# (already-bound courses are skipped).
#
# Usage (run from the directory that contains your target .env):
#   ./adopt_git.sh <LEGACY_TOKEN_SECRET>            # migrate + adopt (writes bindings)
#   ./adopt_git.sh                                  # legacy secret == target's
#   DRY_RUN=1 ./adopt_git.sh <LEGACY_TOKEN_SECRET>  # preview adoption, write nothing
#
# Env knobs:
#   DRY_RUN=1        adopt is dry-run (rolled back); migrate still runs
#   SKIP_RESTART=1   do not restart the container after a successful apply
#   CONTAINER=name   backend container name (default: computor-uvicorn)
#   ENV_FILE=path    override the .env location (default: ./.env in the CWD)
#   GITLAB_BASE_URL= override the git_server base_url (else from org properties.gitlab.url)
#   GITLAB_NAME=     display name for the registered git_server
# ---------------------------------------------------------------------------
set -euo pipefail

CONTAINER="${CONTAINER:-computor-uvicorn}"
LEGACY_TOKEN_SECRET="${1:-}"
if [[ "${DRY_RUN:-0}" == "1" ]]; then APPLY=0; else APPLY=1; fi

# .env in the directory we are executed from (NOT the script's own dir).
ENV_FILE="${ENV_FILE:-$PWD/.env}"
[[ -f "$ENV_FILE" ]] || { echo "ERROR: .env not found at $ENV_FILE (run from the dir containing it)" >&2; exit 1; }
set -a; source "$ENV_FILE"; set +a
: "${TOKEN_SECRET:?TOKEN_SECRET not set in $ENV_FILE — needed to re-encrypt tokens}"
LEG="${LEGACY_TOKEN_SECRET:-$TOKEN_SECRET}"

# container must be up (adopt reads the container's own POSTGRES_* -> postgres:5437).
state="$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)"
[[ "$state" == "true" ]] || { echo "ERROR: container '$CONTAINER' is not running" >&2; exit 1; }

if [[ "$APPLY" == "1" ]]; then MODE="APPLY"; else MODE="DRY-RUN"; fi
echo ">> target .env: $ENV_FILE"
echo ">> container:   $CONTAINER   |   adopt mode: $MODE   |   legacy-secret: $([[ "$LEG" != "$TOKEN_SECRET" ]] && echo custom || echo same-as-target)"

# ===========================================================================
# [1] MIGRATE
# ===========================================================================
echo ">> [1/2] alembic upgrade head ..."
docker exec "$CONTAINER" sh -c 'cd computor-backend/src/computor_backend && alembic upgrade head'
docker exec "$CONTAINER" sh -c 'cd computor-backend/src/computor_backend && alembic current' 2>/dev/null | sed 's/^/     now at: /'

# ===========================================================================
# [2] ADOPT  (runs inside the container; DB comes from the container's own env)
# ===========================================================================
echo ">> [2/2] adopting legacy GitLab config into course_git_binding ..."
env_args=(-e ADOPT_APPLY="$APPLY" -e TOKEN_SECRET="$TOKEN_SECRET" -e LEGACY_TOKEN_SECRET="$LEG")
if [[ -n "${GITLAB_BASE_URL:-}" ]]; then env_args+=(-e GITLAB_BASE_URL="$GITLAB_BASE_URL"); fi
if [[ -n "${GITLAB_NAME:-}" ]];     then env_args+=(-e GITLAB_NAME="$GITLAB_NAME");     fi

docker exec -i "${env_args[@]}" "$CONTAINER" python3 - <<'PYEOF'
import os, sys, json
from sqlalchemy import create_engine, text
try:
    from keycove import encrypt, decrypt   # same primitive computor_types.encryption uses
except Exception as e:
    sys.exit("   !! keycove not importable (%s)" % e)

APPLY      = os.environ.get("ADOPT_APPLY") == "1"
NEW_SECRET = os.environ.get("TOKEN_SECRET") or ""
LEG_SECRET = os.environ.get("LEGACY_TOKEN_SECRET") or NEW_SECRET
BASE_OVER  = (os.environ.get("GITLAB_BASE_URL") or "").rstrip("/") or None
NAME_OVER  = os.environ.get("GITLAB_NAME") or None
if not NEW_SECRET:
    sys.exit("   !! TOKEN_SECRET not set; cannot re-encrypt tokens")

# The CONTAINER's own DB coordinates (compose network: postgres:5437), exactly
# like computor_backend.database — no hardcoded host, no host Python needed.
eng = create_engine("postgresql+psycopg2://%s:%s@%s:%s/%s" % (
    os.environ["POSTGRES_USER"], os.environ["POSTGRES_PASSWORD"],
    os.environ.get("POSTGRES_HOST", "localhost"), os.environ.get("POSTGRES_PORT", "5432"),
    os.environ["POSTGRES_DB"]))

def as_dict(v):
    if v is None: return {}
    if isinstance(v, dict): return v
    try: return json.loads(v)
    except Exception: return {}

def extract_template(cg, base_url):
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
    sys.exit("\n   !! %d course(s) failed token-decrypt -> NOTHING written. Fix the "
             "legacy token and re-run." % len(errors))

if APPLY:
    trans.commit()
    print("\n   === APPLIED: %d created, %d already bound, %d skipped ===" % (created, existing, skipped))
else:
    trans.rollback()
    print("\n   === DRY-RUN: would create %d, %d already bound, %d skipped. "
          "Re-run without DRY_RUN=1 to write. ===" % (created, existing, skipped))
    if errors:
        print("   (%d course(s) would fail token-decrypt with the current legacy secret)" % len(errors))
PYEOF

# ===========================================================================
# restart so the API runs against the migrated schema + adopted data
# ===========================================================================
if [[ "$APPLY" == "1" && "${SKIP_RESTART:-0}" != "1" ]]; then
  echo ">> restarting $CONTAINER (picks up migrated schema; re-runs alembic no-op) ..."
  docker restart "$CONTAINER" >/dev/null
  echo "   (restart temporal-worker too if it was running)"
fi

echo ">> Done."
