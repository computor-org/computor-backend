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
| Sum of all workspaces, **process count** | `MemoryMax`, `CPUQuota`, `TasksMax` of `computor-workspaces.slice` | worker host; **required** when public |
| Writable image layer | `storage_size` (overlay2 on xfs+pquota only) | template variable, opt-in |
| Home/scratch volumes | host disk watchdog (below) | worker host |

The kreuzwerker/docker provider has no per-container pids limit and dockerd has
no default one, so the slice's `TasksMax` is the fork-bomb bound.

A slice name alone proves nothing: Docker creates an unknown slice on the fly
with no limits. With `COMPUTOR_PUBLIC_DEPLOYMENT=true`, the coder worker starts
a throwaway container in the slice and reads the slice's `memory.max`,
`cpu.max` and `pids.max`. Template push and rollout, as well as workspace
provisioning and start in the API (the verification is cached for 5 minutes),
are refused unless all three are limited. Any error also refuses. Coder's own
autostart schedule bypasses the API gate, so do not enable autostart on public
templates.

Install on the worker host:

```bash
sudo install -m 0644 ops/coder/systemd/computor-workspaces.slice /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl start computor-workspaces.slice
# .env on the control plane:
#   COMPUTOR_PUBLIC_DEPLOYMENT=true
#   CODER_WORKSPACE_CGROUP_PARENT=computor-workspaces.slice
# then push all templates (the push always sends the memory/CPU caps).
```

### Home and scratch volumes

Docker named volumes on ext4 have no quota, and a per-workspace loop-mounted
XFS with project quotas is too heavy to operate here. Instead,
`ops/coder/home-watchdog/` has a host-side systemd timer that runs every 10
minutes. It measures every `coder-home-*` and `coder-scratch-*` volume with
`du -sx` on its mountpoint. When a volume is over `COMPUTOR_HOME_LIMIT_GIB`
(default 10), it stops the containers that mount it and alerts through syslog
and the optional `COMPUTOR_HOME_ALERT_URL` webhook. It never deletes data. The
worst case is a disk fill of up to one timer interval of writes, so keep the
Docker data root on its own filesystem with headroom.

```bash
sudo install -m 0755 ops/coder/home-watchdog/computor-home-watchdog.sh /usr/local/sbin/
sudo install -m 0644 ops/coder/home-watchdog/computor-home-watchdog.{service,timer} /etc/systemd/system/
echo 'COMPUTOR_HOME_LIMIT_GIB=10' | sudo tee /etc/default/computor-home-watchdog
sudo systemctl daemon-reload && sudo systemctl enable --now computor-home-watchdog.timer
```

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