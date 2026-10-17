# Coder Integration Guide

## Two Deployment Options

The Computor platform supports Coder in two different ways:

### 1. Integrated Coder (Recommended)
**Location**: `ops/docker/docker-compose.coder.yaml`
**Config**: `.env` (in project root)
**Usage**: Set `CODER_ENABLED=true` in `.env`, then `./computor.sh up dev -d`

- Runs as part of Computor stack
- Has its **own** dedicated PostgreSQL (`computor-coder-postgres`, port 5439)
  — separate from the main Computor postgres
- Has its **own** dedicated Docker registry (`computor-coder-registry`) for
  workspace images, with htpasswd auth
- Managed by main startup/stop scripts
- Single Traefik instance for routing (workspaces reachable at `/coder/{user}/{workspace}/`)

### 2. Standalone Coder
**Location**: `ops/coder/`
**Config**: `ops/coder/.env`
**Usage**: `cd ops/coder && ./install.sh`

- Independent Coder installation
- Own PostgreSQL database
- Separate Docker Compose stack
- Own Traefik instance
- Configured via its own `.env` file

## Configuration Files

### For Integrated Deployment

Create `.env.coder` in project root:
```bash
# From template
cp ops/environments/.env.coder.template .env.coder
# Edit as needed
vim .env.coder
```

Key variables:
- `CODER_DOMAIN` - Your Coder domain
- `CODER_ADMIN_EMAIL` - Admin email
- `CODER_ADMIN_PASSWORD` - Admin password
- Uses shared `POSTGRES_*` from `.env.common`

### For Standalone Deployment

Create `.env` in `ops/coder/`:
```bash
cd ops/coder
cp .env.example .env
vim .env
```

Key variables:
- `CODER_DIR` - Installation directory
- `CODER_POSTGRES_*` - Separate database config
- `CODER_PORT` - External port
- All self-contained

## When to Use Which?

### Use Integrated Coder when:
- You want everything managed together
- You're already running Computor
- You want a shared Docker network and single Traefik routing
- You prefer single-point management

Note: integrated mode does **not** share PostgreSQL with Computor — Coder
gets its own dedicated postgres container (`coder-postgres`).

### Use Standalone Coder when:
- You want Coder independent of Computor
- You're deploying on a separate server
- You need custom PostgreSQL configuration
- You want to manage Coder separately

## Migration Between Modes

### From Standalone to Integrated:
1. Backup Coder data from standalone PostgreSQL
2. Stop standalone Coder: `cd ops/coder && ./stop.sh`
3. Setup integrated: `./setup-env.sh` and configure `.env.coder`
4. Set `CODER_ENABLED=true` in `.env` and start: `./computor.sh up dev -d`
5. Restore data to shared PostgreSQL `coder` database

### From Integrated to Standalone:
1. Backup Coder data from shared PostgreSQL `coder` database
2. Stop integrated: `./computor.sh down dev`
3. Setup standalone: `cd ops/coder && ./install.sh`
4. Restore data to standalone PostgreSQL

## Environment Variable Mapping

| Standalone `.env` | Integrated `.env` | Notes |
|-------------------|-------------------|--------|
| `CODER_DIR` | `CODER_DIR` | Same |
| `CODER_DOMAIN` | `CODER_DOMAIN` | Same |
| `CODER_PORT` | `CODER_EXTERNAL_PORT` | Different naming |
| `CODER_POSTGRES_PORT` | hard-coded `5439` | Separate DB instance |
| `CODER_POSTGRES_USER` | `CODER_POSTGRES_USER` | Required (no default); separate from main `POSTGRES_USER` |
| `CODER_POSTGRES_PASSWORD` | `CODER_POSTGRES_PASSWORD` | Required (no default); separate from main `POSTGRES_PASSWORD` |
| `CODER_ADMIN_EMAIL` | `CODER_ADMIN_EMAIL` | Same |
| `CODER_ADMIN_PASSWORD` | `CODER_ADMIN_PASSWORD` | Same |
| `DOCKER_GID` | `DOCKER_GID` | Same |

## Quick Start

### Integrated Coder (Recommended)
```bash
# Setup environment
./setup-env.sh

# Start Computor with Coder
./computor.sh up dev -d

# Access Coder
# https://your-coder-domain:8446
```

### Standalone Coder
```bash
# Navigate to deployment directory
cd ops/coder

# Configure
cp .env.example .env
vim .env

# Install and start
./install.sh -D coder.example.com -P 8446 \
  -u admin -e admin@example.com -w secretpass

# Access Coder
# https://coder.example.com:8446
```

## Integration with Computor Backend

When Coder is enabled (either mode), the Computor backend can:
- Create Coder users automatically
- Provision workspaces for students
- Manage workspace lifecycles
- Provide SSO integration

The backend uses these environment variables:
- `CODER_ENABLED` - Enable Coder features
- `CODER_URL` - Internal API URL
- `CODER_ADMIN_API_SECRET` - API authentication

## Public Deployment: Workspace Resource Bounds

Workspaces run untrusted code, often with root. Set
`COMPUTOR_PUBLIC_DEPLOYMENT=true` on a public instance: `computor.sh` and the
API then refuse to build, push or roll out templates unless every bound below
that can be enforced is in place.

| Resource | Bound | Where |
|---|---|---|
| RAM per workspace | `memory_mb` (default 3072, MATLAB 6144), swap off | template; always pushed explicitly |
| CPU per workspace | `cpus` (default 2) | template; always pushed explicitly |
| Processes per workspace | `TasksMax` of each `computor-workspaces-<id>.slice` (drop-in `computor-workspaces-.slice.d/`) | worker host |
| Sum of all workspaces, **process count** | `MemoryMax`, `CPUQuota`, `TasksMax` of `computor-workspaces.slice` | worker host; **required** when public |
| Capabilities | all dropped; with root, only those sudo/apt need; no-new-privileges without root | template |
| Writable image layer | `storage_size` (overlay2 on xfs+pquota only) | template variable, opt-in |
| Home/scratch volumes | host disk watchdog (below) | worker host |

The kreuzwerker/docker provider has no per-container pids limit and dockerd has
no default one, so systemd supplies the fork-bomb bound. With a `.slice`
parent, each template places its workspace in its own child slice
`computor-workspaces-<workspace id without dashes>.slice`. The drop-in
`ops/coder/systemd/computor-workspaces-.slice.d/50-per-workspace.conf` gives
every child `TasksMax=4096`; the aggregate slice's `TasksMax` bounds the sum.
Without the drop-in, a child slice is unlimited and only the aggregate applies.

A slice name alone proves nothing: Docker creates an unknown slice on the fly
with no limits. With `COMPUTOR_PUBLIC_DEPLOYMENT=true`, the coder worker reads
the slice's `memory.max`, `cpu.max` and `pids.max` from the host's cgroup2
tree, which compose mounts read-only at `/host/sys/fs/cgroup`. The slice must
be active, hence `enable --now` below. Template push and rollout, as well as workspace
provisioning and start in the API (the verification is cached for 5 minutes),
are refused unless all three are limited. Any error also refuses. Coder's own
autostart schedule bypasses the API gate, so do not enable autostart on public
templates.

Install on the worker host:

```bash
sudo install -m 0644 ops/coder/systemd/computor-workspaces.slice /etc/systemd/system/
sudo install -d /etc/systemd/system/computor-workspaces-.slice.d
sudo install -m 0644 ops/coder/systemd/computor-workspaces-.slice.d/50-per-workspace.conf \
    /etc/systemd/system/computor-workspaces-.slice.d/
sudo systemctl daemon-reload && sudo systemctl enable --now computor-workspaces.slice
# .env on the control plane:
#   COMPUTOR_PUBLIC_DEPLOYMENT=true
#   CODER_WORKSPACE_CGROUP_PARENT=computor-workspaces.slice
# then push all templates (the push always sends the memory/CPU caps).
```

### Home/scratch volumes and writable layers

Docker named volumes on ext4 have no quota, and overlay2 on ext4 cannot limit
the writable layer either. Real byte and inode quotas (XFS project quotas on
the Docker data root) are a tracked follow-up. Until then,
`ops/coder/home-watchdog/` is supplementary monitoring with after-the-fact
enforcement, not a quota:

- A systemd timer runs it every 60 s.
- It measures every `coder-home-*`/`coder-scratch-*` volume (`du -sx`) and
  every running workspace container's writable layer (`docker inspect --size`,
  which covers `/tmp`, `/var` and so on).
- Over `COMPUTOR_HOME_LIMIT_GIB` (default 10) or `COMPUTOR_LAYER_LIMIT_GIB`
  (default 5) it stops the containers concerned. It alerts through syslog and
  the optional `COMPUTOR_HOME_ALERT_URL`, and never deletes data.
- An error on one object is reported and the scan continues. Exit status 2 plus
  an "enforcement INCOMPLETE" alert means something could not be measured or
  stopped.
- Between two runs a workspace can still write at full disk speed. Keep the
  Docker data root on its own filesystem with headroom.

```bash
sudo install -m 0755 ops/coder/home-watchdog/computor-home-watchdog.sh /usr/local/sbin/
sudo install -m 0644 ops/coder/home-watchdog/computor-home-watchdog.{service,timer} /etc/systemd/system/
echo 'COMPUTOR_HOME_LIMIT_GIB=10' | sudo tee /etc/default/computor-home-watchdog
sudo systemctl daemon-reload && sudo systemctl enable --now computor-home-watchdog.timer
```

### Coder worker Docker access and host operations

`temporal-worker-coder` has no Docker socket. It reaches Docker through
`coder-worker-socket-proxy`, on a private internal network, whose
`ops/docker/coder-worker-socket-proxy/haproxy.cfg.template` allows only the
calls the worker makes: build, image tag/push/inspect/untag, distribution
inspect, volume inspect/delete of `coder-home-*`/`coder-scratch-*` and
`system df`. Container create and exec, volume create and image pull are
refused, as are build parameters that leave the default build sandbox
(`networkmode`, `cgroupparent`, `remote`, BuildKit `version`/`session`/`outputs`).
Image names the worker builds, tags, pushes or removes must start with the
proxy's `CODER_REGISTRY_HOST/` (compose sets it to the worker's value,
`localhost:5000`), so the worker cannot retag an image the host runs by tag
or push a host image to another registry.
The upstream proxy's env switches filter only by path prefix, and any client
allowed container create is root on the host; so the template replaces them.
`ops/tests/test_coder_worker_socket_proxy.sh` probes it against a local daemon
(also run in CI).

Builds remain root-adjacent by design: classic-builder `RUN` steps run as
root in a default bridge container with egress, and a Dockerfile `ADD <url>`
is fetched by dockerd itself, in the host network namespace. A template can
therefore reach services listening on the worker host and the cloud metadata
endpoint. This exposure predates the proxy (the raw socket allowed the same);
restrict it with a host egress rule if templates are not trusted.

The two operations that needed a container now run on the worker host, as
root, from a spool the worker mounts at `/hostops`:

- the volume-ownership repair (`chown -R 1000:1000` in a throwaway container
  with no network and only the file capabilities; its image is pinned by
  digest, `COMPUTOR_REPAIR_IMAGE` overrides it);
- registry tag pruning and `registry garbage-collect` after a template build,
  serialised against pushes by `registry.lock`.

`computor-coder-hostops.path` starts `computor-coder-hostops.service` whenever
a request is queued; the worker waits for the answer, so the admin UI and the
build workflow report the result as before. Install on the worker host before
starting the new worker image:

```bash
sudo install -m 0755 ops/coder/hostops/computor-coder-hostops.sh /usr/local/sbin/
sudo install -m 0644 ops/coder/hostops/computor-coder-hostops.{service,path} /etc/systemd/system/
sudo install -m 0644 ops/coder/hostops/computor-coder-hostops.tmpfiles \
    /etc/tmpfiles.d/computor-coder-hostops.conf
# Only if the registry container is not computor-coder-registry:
#   echo 'COMPUTOR_REGISTRY_CONTAINER=<name>' | sudo tee /etc/default/computor-coder-hostops
sudo systemd-tmpfiles --create /etc/tmpfiles.d/computor-coder-hostops.conf
sudo systemctl daemon-reload && sudo systemctl enable --now computor-coder-hostops.path
```

The tmpfiles entry gives uid 1000 (the worker's user) write access to the
spool's `requests/`. Check that the worker image runs as uid 1000
(`docker run --rm --entrypoint id <worker image>`) and that no other host
account has uid 1000 (`getent passwd 1000`); such an account could queue
chown or GC requests (limited to workspace volumes and the registry).

Without them, repairs fail with "host operations are not set up" and builds
skip the registry garbage collection (reported in the build result).

## Troubleshooting

### Port Conflicts
If running both modes on the same machine, ensure different ports:
- Integrated uses ports from `.env.coder`
- Standalone uses ports from `ops/coder/.env`

### Database Issues
- Integrated: Check `computor-coder-postgres` container (port 5439) is running
- Standalone: Check separate PostgreSQL container is running

### Network Issues
- Integrated: All services on `computor-network`
- Standalone: Separate `coder-network`

## Best Practices

1. **Don't mix modes** - Use either integrated OR standalone, not both
2. **Backup before switching** - Always backup Coder data
3. **Check ports** - Avoid conflicts between modes
4. **Use integrated for development** - Easier management
5. **Consider standalone for production** - Better isolation