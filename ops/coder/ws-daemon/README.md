# Workspace Docker daemon and per-home filesystems (computor.at worker)

Coder workspaces run on a second dockerd (`dockerd-ws.service`) and never on
the main daemon that runs grading workers, the registry, Postgres and Coder.

- **Daemon:** `daemon-ws.json`. Socket `/run/computor-ws-docker/docker.sock`
  (root only, directory kept across restarts so bind mounts of it stay valid),
  data-root `/var/lib/docker-ws`, exec-root `/run/docker-ws`, containerd
  namespace `computor-ws`, `userns-remap: computor-ws` (container uid 1000 =
  host uid 2001000), `no-new-privileges`, `live-restore`, `iptables: false`,
  default bridge on its own link `computor-ws0` (created by the unit; with
  `bridge: none` dockerd would delete the host's `docker0` on a start without
  running containers, which broke the main daemon's default network on
  2026-10-25).
- **Coder** reaches only this daemon, through `coder-provisioner-socket-proxy`
  (`CODER_WORKSPACE_DOCKER_MOUNT=/run/computor-ws-docker`,
  `CODER_WORKSPACE_DOCKER_SOCKET=/var/run/workspace-docker/docker.sock`).
- **Data-root:** a sparse XFS image (`/var/lib/computor-ws/dataroot.img`,
  `prjquota`, loop with direct I/O set by `dockerd-ws.service`) bounds all workspace images and layers and
  lets overlay2 enforce `storage_size` per container. No `nodev` on it:
  overlay2's quota probe needs a device node there.
- **Homes:** `computor-ws-homes.py` is a Docker volume plugin (driver
  `computor-home`). Docker probes every driver for an unknown volume name, and
  the plugin claims `coder-home-<uuid>` and `coder-scratch-<uuid>`, so the
  templates' volume names are unchanged. Each volume is a sparse ext4 image in
  `/var/lib/computor-ws/homes`, loop-mounted (direct I/O, `nodev,nosuid`) by
  the host when a container needs it. Default 5G (`/etc/default/computor-ws-homes`,
  per-volume sizes in `/etc/computor/ws-home-sizes`, grow with
  `computor-ws-home-grow`). Home volumes cannot be removed through Docker.
- **Fail closed:** if the plugin is unreachable, Docker would create an
  unknown `coder-home-*` as an unlimited local volume. `install.sh` makes the
  daemon's local-volume directory (`<DockerRootDir>/volumes`) immutable
  (`chattr +i`), so any local volume create fails with EPERM and the
  workspace does not start (verified 2026-10-25 with the plugin socket
  removed). `dockerd-ws` also `Requires=` the plugin service.
- **Admin operations:** the coder worker lists and deletes these homes
  through `ops/coder/hostops` (`list-volumes`, `delete-volume`;
  worker env `CODER_WORKSPACE_VOLUMES_HOSTOPS=true`), and the ownership
  repair (`chown-volume`) runs on this daemon, all with
  `COMPUTOR_WORKSPACE_DOCKER=unix:///run/computor-ws-docker/docker.sock` in
  `/etc/default/computor-coder-hostops`. The home watchdog runs against this
  daemon with `DOCKER_HOST` set in `/etc/default/computor-home-watchdog`
  (homes and rootfs have hard sizes, so it is a second line only; keep
  `COMPUTOR_LAYER_LIMIT_GIB` above `CODER_WORKSPACE_ROOTFS_SIZE`).
- **Disk bound (sparse images):** the images allocate on write, so the host
  disk is shared, not reserved. Worst case on the host filesystem of
  `/var/lib/computor-ws` = data-root size + sum of all home and scratch image
  sizes (2026-10-25: 120G + 17 x 5G = 205G against ~300G free). The
  computor-infra sentinel alerts when the host's free space is below the
  images' remaining growth (overcommit) or a disk passes 85%.
- **Network:** `docker-compose.workspace-daemon.yaml` (project `computor-ws`)
  creates the workspace networks on this daemon (172.30.0.0/20 online,
  172.30.16.0/20 internal) and runs the workspace ingress there with its own
  read-only Docker proxy. The ingress also answers as `coder` and relays the
  agents' TCP stream to the Coder server's published address
  (`coder-relay.yml`, rendered from `ops/coder/workspace-ingress/coder-relay.yml.template`).
  The firewall for these bridges (policy, forwarding, NAT, internal network)
  comes from computor-infra `prod/workspace-egress.sh`.

## Rehearsed (2026-10-25, worker host, copies of three real homes)
Manifests equal after migration (2732, 344, 688 entries). Home fill: ENOSPC at
4.8G, the other home unaffected. `/tmp` tmpfs ENOSPC at 512M, rootfs ENOSPC at
its 1G `storage_opt`. Project-id change (FS_IOC_FSSETXATTR) refused with EINVAL
for container root with the root-mode capabilities; `mount`, `unshare -U`,
`/proc/sys` writes refused. Host uid of workspace processes 2001000. Agent
relay to Coder from online and offline networks; ws to ws, ws to host, ws to
prod and registry refused; internet only from the online network.
Without direct I/O on the loop devices a large write OOM-killed the workspace.

## Install and cut-over
1. `ops/coder/ws-daemon/install.sh` (as root on the worker, from the checkout).
2. Render `coder-relay.yml` into `${SYSTEM_DEPLOYMENT_PATH}/workspace-ingress/dynamic/`
   (`CODER_RELAY_UPSTREAM=<wg address>:7080 envsubst`).
3. Stop the main-daemon ingress and its proxy (now in profile `legacy-ingress`),
   start `docker-compose.workspace-daemon.yaml` against the workspace daemon,
   install the new `computor-workspace-egress`.
4. Pull the active workspace images into the workspace daemon.
5. Per home volume, with workspaces stopped: `migrate-home.py coder-home-<id>`
   (manifest before and after, owners shifted into the remap range).
6. Set the .env variables above plus `CODER_WORKSPACE_ROOTFS_SIZE` and
   `CODER_WORKSPACE_TMP_SIZE` (API host), recreate the provisioner proxy, push
   templates.

Rollback: point the provisioner proxy back at the main socket, `COMPOSE_PROFILES=legacy-ingress`
for the main-daemon ingress, stop `dockerd-ws`. The old home volumes are not
touched by the migration.
