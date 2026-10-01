#!/bin/bash
# Exercise the Docker lifecycle used by Coder workspace containers.
set -euo pipefail

templates_root=$(cd "$(dirname "$0")/../coder/templates" && pwd)
for template in bash jupyter matlab-ui matlab-vscode ubuntu-desktop vscode; do
    config="$templates_root/$template/container.tf"
    grep -Eq '^[[:space:]]*restart[[:space:]]*=[[:space:]]*"unless-stopped"' "$config"
    grep -Eq '^[[:space:]]*count[[:space:]]*=[[:space:]]*data.coder_workspace.me.start_count' "$config"
done
grep -q -- '--disable-workspace-trust' "$templates_root/matlab-vscode/startup.sh.tftpl"

name="computor-restart-test-$$"
image="alpine@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6"
cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; }
trap cleanup EXIT

# Keep PID 1 alive long enough for Docker to enable the restart policy, then
# fail inside the container. No user volume, network, daemon restart or host
# service is involved.
docker run -d --name "$name" --restart unless-stopped --network none \
    --read-only --cap-drop ALL --security-opt no-new-privileges \
    --memory 32m --pids-limit 16 --log-driver none \
    "$image" sh -c 'sleep 11; exit 1' >/dev/null

restarted=false
for _ in $(seq 1 45); do
    if [ "$(docker inspect --format '{{.RestartCount}}' "$name")" -gt 0 ]; then
        restarted=true
        break
    fi
    sleep 1
done
[ "$restarted" = true ] || { echo 'Container did not restart after PID 1 failed' >&2; exit 1; }

docker stop "$name" >/dev/null
[ "$(docker inspect --format '{{.State.Running}}' "$name")" = false ]
stopped_count=$(docker inspect --format '{{.RestartCount}}' "$name")
sleep 3
[ "$(docker inspect --format '{{.State.Running}}' "$name")" = false ]
[ "$(docker inspect --format '{{.RestartCount}}' "$name")" = "$stopped_count" ]

docker rm "$name" >/dev/null
trap - EXIT
if docker inspect "$name" >/dev/null 2>&1; then
    echo 'Container still exists after explicit remove' >&2
    exit 1
fi
echo 'Workspace container restart, stop, and remove behavior passed'
