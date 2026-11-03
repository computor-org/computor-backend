# Workspace Docker daemon and per-home filesystems (worker host)

Coder workspaces run on a second dockerd (`dockerd-ws.service`) and never on
the main daemon that runs grading workers, the registry, Postgres and Coder.

- **Daemon:** `daemon-ws.json`. Socket `/run/computor-ws-docker/docker.sock`
  (root only, directory kept across restarts so bind mounts of it stay valid),
  data-root `/var/lib/docker-ws`, exec-root `/run/docker-ws`, containerd
  namespace `computor-ws`, `userns-remap: computor-ws` (container uid 1000 =
  host uid 2001000), `no-new-privileges`, `live-restore`, `iptables: false`,
  default bridge on its own link `computor-ws0` (created by the unit; with
  `bridge: none` dockerd would delete the host's `docker0` on a start without
  running containers, which breaks the main daemon's default network).
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
  workspace does not start. `dockerd-ws` also `Requires=` the plugin service.
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
  sizes. Monitor that the host's free space stays above the images'
  remaining growth (overcommit).
- **Network:** `docker-compose.workspace-daemon.yaml` (project `computor-ws`)
  creates the workspace networks on this daemon (172.30.0.0/20 online,
  172.30.16.0/20 internal) and runs the workspace ingress there with its own
  read-only Docker proxy. The ingress also answers as `coder` and relays the
  agents' TCP stream to the Coder server's published address
  (`coder-relay.yml`, rendered from `ops/coder/workspace-ingress/coder-relay.yml.template`).
  The firewall for these bridges (policy, forwarding, NAT, internal network)
  is host configuration and not part of this repository.

## Install and cut-over
1. `ops/coder/ws-daemon/install.sh` (as root on the worker, from the checkout).
2. Render `coder-relay.yml` into `${SYSTEM_DEPLOYMENT_PATH}/workspace-ingress/dynamic/`
   (`CODER_RELAY_UPSTREAM=<wg address>:7080 envsubst`).
3. Stop the main-daemon ingress and its proxy, start
   `docker-compose.workspace-daemon.yaml` against the workspace daemon, and
   install the egress firewall for the workspace bridges.
4. Pull the active workspace images into the workspace daemon.
5. Per home volume, with workspaces stopped: `migrate-home.py coder-home-<id>`
   (manifest before and after, owners shifted into the remap range).
6. Set the .env variables above plus `CODER_WORKSPACE_ROOTFS_SIZE` and
   `CODER_WORKSPACE_TMP_SIZE` (API host), recreate the provisioner proxy, push
   templates.

Rollback: point the provisioner proxy back at the main socket, start the
main-daemon ingress again, stop `dockerd-ws`. The old home volumes are not
touched by the migration.
