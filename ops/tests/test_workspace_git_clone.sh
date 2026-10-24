#!/bin/bash
# A managed-Forgejo student repository can be cloned through the
# workspace-facing git route (computor-org/issues#433).
#
# Starts the pinned Forgejo and workspace-ingress images on private networks:
# Forgejo on a backend network, a git client on an internal "workspace"
# network that only workspace-ingress (rendered from this repo's
# routes.yml.template) also joins, under its computor-git alias. The backend's
# own Forgejo provider then provisions a synthetic student exactly as
# provision-repository does — account, copy of the course template, write grant
# on it, read grant on the template, clone token — and renders the clone URLs
# for a workspace caller. From inside the workspace network the client must
# clone through http://computor-git/, push to its own repository, read the
# template and be refused a push to it. Each failure names its phase, and git's
# exit code and stderr are shown with the credential redacted.
#
# Requires a local Docker daemon and uv; nothing leaves this host. The
# credential lives only in a 0600 file under a private temp directory.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
repo_root=$(cd "$here/../.." && pwd)
template="$here/../coder/workspace-ingress/dynamic/routes.yml.template"
pin() { grep -m1 -o "image: $1[^ ]*" "$2" | cut -d' ' -f2; }
forgejo_image=$(pin "codeberg.org/forgejo/forgejo:" "$here/../docker/docker-compose.forgejo.yaml")
ingress_image=$(pin "traefik:" "$here/../docker/docker-compose.coder.yaml")
git_image="${GIT_IMAGE:-alpine/git:v2.49.1}"
tag="wsgit-test-$$"
root_url="https://computor.invalid/forgejo"
admin=smoke-admin
admin_password="synthetic-$(head -c 12 /dev/urandom | od -An -tx1 | tr -d ' \n')"
port=$(python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')
work=$(mktemp -d)
chmod 700 "$work"

cleanup() {
    docker rm -f "$tag-forgejo" "$tag-ingress" >/dev/null 2>&1 || true
    docker network rm "$tag-ws" "$tag-backend" >/dev/null 2>&1 || true
    rm -rf "$work"
}
trap cleanup EXIT

docker network create "$tag-backend" >/dev/null
docker network create --internal "$tag-ws" >/dev/null

# Forgejo listens on the published port inside the container too: the backend
# provider self-migrates the template from its own base URL, which therefore has
# to resolve to Forgejo both from this host and from inside the container.
docker run -d --name "$tag-forgejo" --network "$tag-backend" \
    -p "127.0.0.1:$port:$port" \
    -e FORGEJO__database__DB_TYPE=sqlite3 \
    -e FORGEJO__security__INSTALL_LOCK=true \
    -e FORGEJO__server__HTTP_PORT="$port" \
    -e FORGEJO__server__ROOT_URL="$root_url" \
    -e FORGEJO__server__DISABLE_SSH=true \
    -e FORGEJO__service__DISABLE_REGISTRATION=true \
    -e FORGEJO__service__REQUIRE_SIGNIN_VIEW=true \
    -e FORGEJO__repository__DEFAULT_PRIVATE=true \
    -e FORGEJO__migrations__ALLOW_LOCALNETWORKS=true \
    -e FORGEJO__migrations__ALLOWED_DOMAINS=127.0.0.1 \
    "$forgejo_image" >/dev/null

WORKSPACE_INGRESS_BACKEND_URL="http://127.0.0.1:9" \
WORKSPACE_INGRESS_GIT_URL="http://$tag-forgejo:$port" \
    envsubst '${WORKSPACE_INGRESS_BACKEND_URL} ${WORKSPACE_INGRESS_GIT_URL}' \
    < "$template" > "$work/routes.yml"
chmod 644 "$work/routes.yml"
chmod 755 "$work"
mkdir "$work/secret"
chmod 700 "$work/secret"
docker create --name "$tag-ingress" --network "$tag-backend" \
    --user 65534:65534 --cap-drop ALL --read-only \
    -v "$work/routes.yml:/etc/traefik/dynamic/routes.yml:ro" \
    "$ingress_image" \
    --entrypoints.web.address=:80 \
    --providers.file.directory=/etc/traefik/dynamic >/dev/null
docker network connect --alias computor-git --alias computor-api "$tag-ws" "$tag-ingress"
docker start "$tag-ingress" >/dev/null

for _ in $(seq 1 90); do
    curl -fs "http://127.0.0.1:$port/api/healthz" >/dev/null 2>&1 && break
    sleep 2
done
curl -fs "http://127.0.0.1:$port/api/healthz" >/dev/null || { echo "FAIL: Forgejo did not become healthy" >&2; exit 1; }
docker exec -u git "$tag-forgejo" forgejo admin user create --admin \
    --username "$admin" --password "$admin_password" \
    --email "$admin@example.invalid" --must-change-password=false >/dev/null

echo "== provision (backend Forgejo provider, workspace audience)"
uv run --quiet --project "$repo_root/computor-backend" python "$here/workspace_git_provision.py" \
    "http://127.0.0.1:$port" "$root_url" "$admin" "$admin_password" "$work/secret/clone.json"
python3 - "$work/secret/clone.json" "$work/secret/clone.env" <<'PY'
import json, os, sys
c = json.load(open(sys.argv[1]))
fd = os.open(sys.argv[2], os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as out:
    for key in ("student_url", "template_url", "username", "token"):
        out.write(f"{key.upper()}={c[key]}\n")
PY

echo "== clone through workspace-ingress"
# Phases print "ok <phase>" or "FAIL <phase>: exit <code>: <stderr>"; the
# credential is replaced before anything is printed.
set +e
out=$(docker run --rm --network "$tag-ws" --env-file "$work/secret/clone.env" \
    -e GIT_TERMINAL_PROMPT=0 --entrypoint sh "$git_image" -c '
redact() { sed "s/$TOKEN/<redacted>/g"; }
phase() {
    name=$1; shift
    if err=$("$@" 2>&1); then echo "ok $name"; else echo "FAIL $name: exit $?: $(echo "$err" | redact | tail -3 | tr "\n" " ")"; fi
}
refuse() {
    name=$1; reason=$2; shift 2
    if err=$("$@" 2>&1); then echo "FAIL $name: exit 0, expected a refusal"
    elif why=$(echo "$err" | redact | grep -m1 -oiE "$reason"); then echo "ok $name ($why)"
    else echo "FAIL $name: refused for another reason: $(echo "$err" | redact | tail -3 | tr "\n" " ")"; fi
}
git config --global user.name "Synthetic Student"
git config --global user.email student42@example.invalid
git config --global credential.helper "!f() { echo username=\$USERNAME; echo password=\$TOKEN; }; f"
cd /tmp
if ! getent hosts computor-git >/dev/null; then echo "FAIL isolation: computor-git does not resolve"
elif getent hosts '"$tag-forgejo"' >/dev/null; then echo "FAIL isolation: Forgejo resolves directly"
else echo "ok isolation"; fi
phase "clone own repository" timeout 60 git clone -q "$STUDENT_URL" own
phase "commit" sh -c "cd own && echo smoke > smoke.txt && git add smoke.txt && git commit -qm smoke"
phase "push own repository" sh -c "cd own && timeout 60 git push -q origin HEAD"
phase "pushed commit visible" sh -c "timeout 60 git clone -q \"$STUDENT_URL\" again && test -f again/smoke.txt"
phase "read template" timeout 60 git ls-remote -q "$TEMPLATE_URL" HEAD
refuse "push to template refused" "403|not allowed|denied|forbidden" sh -c "cd own && timeout 60 git push -q \"$TEMPLATE_URL\" HEAD:refs/heads/smoke"
refuse "wrong token refused" "401|Authentication failed|invalid credentials" sh -c "TOKEN=wrong-token; export TOKEN; timeout 60 git ls-remote -q \"$STUDENT_URL\""
')
set -e
echo "$out"
failed=$(grep -c '^FAIL' <<<"$out" || true)
passed=$(grep -c '^ok' <<<"$out" || true)
if [ "$failed" -ne 0 ] || [ "$passed" -ne 8 ]; then
    echo "FAIL: $failed phase(s) failed, $passed of 8 passed" >&2
    exit 1
fi
echo "OK: $passed phases"
