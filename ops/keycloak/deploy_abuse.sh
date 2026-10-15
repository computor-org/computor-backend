#!/usr/bin/env bash
# Host-local targeted rollout: snapshot, restart only Keycloak, reconcile, rollback on failure.
# Run from a git-pinned backend checkout: sudo ops/keycloak/deploy_abuse.sh /path/to/tested.jar
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
jar="${1:?Usage: deploy_abuse.sh TESTED_PROVIDER_JAR}"
[[ -f "$jar" ]] || { echo 'Provider JAR not found' >&2; exit 1; }
# shellcheck source=../lib/common.sh
source "$repo/ops/lib/common.sh"
load_env
[[ "${PUBLIC_DOMAIN:-}" == https://computor.at ]] || die 'This rollout is for computor.at only'
[[ "${UPDATE_ENABLED:-false}" != true ]] || die 'Disable concurrent self-updates first'
data="${SYSTEM_DEPLOYMENT_PATH:?}"
mkdir -p "$data/rotation" "$data/keycloak-abuse-releases"
mkdir "$data/rotation/.lock" || die 'Another deployment holds the rotation lock'
release=$(mktemp -d "$data/keycloak-abuse-releases/$(date -u +%Y%m%dT%H%M%SZ).XXXXXXXX")
chmod 0700 "$release"
printf '%s\n' "keycloak-abuse $(git -C "$repo" rev-parse HEAD)" > "$data/rotation/.lock/owner"
succeeded=0
changed=0
restore() {
    local rc=$?
    trap - EXIT
    if (( ! succeeded && changed )); then
        echo "Rollout failed; restoring Keycloak config/theme/provider from $release" >&2
        if [[ -f "$release/realm-before.json" ]]; then
            if ! python3 "$here/setup_abuse.py" --env "$repo/.env" --restore "$release/realm-before.json"; then
                echo 'Automatic config restore failed; retaining provider/env so configured flows stay loadable. Recover from the private snapshot before removing the provider.' >&2
                rm -rf "$data/rotation/.lock"
                exit 1
            fi
        fi
        docker stop computor-keycloak >/dev/null || true
        find "$data/keycloak/themes" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
        cp -a "$release/themes/." "$data/keycloak/themes/"
        find "$data/keycloak/providers" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
        cp -a "$release/providers/." "$data/keycloak/providers/"
        cp -p "$release/env" "$repo/.env"
        # Older env files omit these keys; do not retain exports from the failed rollout.
        unset KEYCLOAK_ABUSE_PROTECTION KEYCLOAK_ABUSE_SECRET KEYCLOAK_ABUSE_COST KEYCLOAK_ABUSE_TTL
        load_env; derive_public_urls prod; pin_project_name; assemble_compose_files prod
        compose up -d --no-deps keycloak || rc=1
    fi
    rm -rf "$data/rotation/.lock"
    exit "$rc"
}
trap restore EXIT
cp -p "$repo/.env" "$release/env"
cp -a "$data/keycloak/themes" "$release/themes"
mkdir -p "$data/keycloak/providers"
cp -a "$data/keycloak/providers" "$release/providers"
docker exec computor-keycloak-db pg_dump -U keycloak keycloak | gzip > "$release/keycloak.sql.gz"
docker ps --filter label=com.docker.compose.project=computor --format '{{.ID}} {{.Names}}' | sort > "$release/containers-before"
sha256sum "$jar" > "$release/provider.sha256"
git -C "$repo" rev-parse HEAD > "$release/source-commit"
changed=1
python3 - "$repo/.env" <<'PY'
from pathlib import Path
import re,secrets,sys
p=Path(sys.argv[1]);text=p.read_text()
values={}
for line in text.splitlines():
    if '=' in line and not line.startswith('#'):
        k,v=line.split('=',1);values[k.strip()]=v.strip().strip('"\'')
for key,value in {'KEYCLOAK_ABUSE_PROTECTION':'true',
                  'KEYCLOAK_ABUSE_SECRET':values.get('KEYCLOAK_ABUSE_SECRET') or secrets.token_urlsafe(48),
                  'KEYCLOAK_ABUSE_COST':values.get('KEYCLOAK_ABUSE_COST') or '10000',
                  'KEYCLOAK_ABUSE_TTL':values.get('KEYCLOAK_ABUSE_TTL') or '300'}.items():
    pattern=re.compile(r'^'+re.escape(key)+r'=.*$',re.M)
    text=pattern.sub(key+'='+value,text) if pattern.search(text) else text.rstrip()+'\n'+key+'='+value+'\n'
p.write_text(text)
PY
install -m 0644 "$jar" "$data/keycloak/providers/computor-keycloak-abuse.jar"
# Stop before swapping the mounted theme tree so no in-flight page mixes versions.
docker stop computor-keycloak >/dev/null
cp -a "$repo/data/keycloak/themes/." "$data/keycloak/themes/"
chmod -R a+rX "$data/keycloak/themes" "$data/keycloak/providers"
load_env; derive_public_urls prod; pin_project_name; assemble_compose_files prod
compose up -d --no-deps keycloak
healthy=0
for _ in $(seq 1 90); do
    if [[ "$(docker inspect -f '{{.State.Health.Status}}' computor-keycloak)" == healthy ]]; then healthy=1; break; fi
    sleep 2
done
(( healthy )) || die 'Keycloak did not become healthy'
python3 "$here/setup_abuse.py" --env "$repo/.env" --apply --backup "$release/realm-before.json"
# A second reconcile proves the deployed flow remains usable/idempotent.
python3 "$here/setup_abuse.py" --env "$repo/.env" --apply
docker ps --filter label=com.docker.compose.project=computor --format '{{.ID}} {{.Names}}' | sort > "$release/containers-after"
succeeded=1
echo "Keycloak protection activated; rollback snapshots: $release"
