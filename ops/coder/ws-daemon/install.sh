#!/usr/bin/env bash
# Install or refresh the workspace Docker daemon on the worker host (as root,
# from the backend checkout root). Idempotent; changes nothing in the main
# dockerd. See README.md for the design and the cut-over.
#   DATAROOT_SIZE  size of the new data-root image (default 120G, sparse)
#   SUBID_BASE     first host uid/gid of the computor-ws range (default 2000000)
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
DATAROOT_SIZE="${DATAROOT_SIZE:-120G}"
SUBID_BASE="${SUBID_BASE:-2000000}"

getent passwd computor-ws >/dev/null ||
    useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin computor-ws
for f in /etc/subuid /etc/subgid; do
    touch "$f"
    if ! grep -q '^computor-ws:' "$f"; then
        # Refuse an overlap with any existing range.
        awk -F: -v b="$SUBID_BASE" '$2+0 < b+65536 && $2+$3 > b {bad=1} END {exit bad}' "$f" ||
            { echo "SUBID_BASE $SUBID_BASE overlaps a range in $f" >&2; exit 1; }
        echo "computor-ws:${SUBID_BASE}:65536" >> "$f"
    fi
done

install -d -m 0700 /var/lib/computor-ws /var/lib/computor-ws/homes
install -d -m 0711 /var/lib/computor-ws/mnt /var/lib/docker-ws
install -d -m 0755 /etc/computor /usr/local/libexec
if [ ! -e /var/lib/computor-ws/dataroot.img ]; then
    truncate -s "$DATAROOT_SIZE" /var/lib/computor-ws/dataroot.img.new
    chmod 0600 /var/lib/computor-ws/dataroot.img.new
    mkfs.xfs -q /var/lib/computor-ws/dataroot.img.new
    mv /var/lib/computor-ws/dataroot.img.new /var/lib/computor-ws/dataroot.img
fi
install -m 0644 "$here/daemon-ws.json" /etc/docker/daemon-ws.json
install -m 0755 "$here/computor-ws-homes.py" /usr/local/libexec/computor-ws-homes.py
install -m 0755 "$here/computor-ws-home-grow.sh" /usr/local/sbin/computor-ws-home-grow
[ -e /etc/default/computor-ws-homes ] || install -m 0644 "$here/computor-ws-homes.default" /etc/default/computor-ws-homes
install -m 0644 "$here/dockerd-ws.service" "$here/computor-ws-homes.service" \
    "$here/var-lib-docker\\x2dws.mount" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now 'var-lib-docker\x2dws.mount' computor-ws-homes.service dockerd-ws.service
for i in $(seq 30); do docker -H unix:///run/computor-ws-docker/docker.sock info >/dev/null 2>&1 && break; sleep 1; done
docker -H unix:///run/computor-ws-docker/docker.sock info --format 'workspace daemon: {{.ServerVersion}} {{.Driver}} {{.DockerRootDir}} {{.SecurityOptions}}'
