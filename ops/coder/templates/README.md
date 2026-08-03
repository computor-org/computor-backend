# Coder Workspace Templates

Each subdirectory is one workspace type. Templates are discovered, built and
pushed automatically — there is no registration list in code.

## Template contract

A template directory must contain:

| File | Purpose |
|---|---|
| `template.json` | Manifest (see below). Its presence makes the directory a template. |
| `*.tf` | Coder Terraform template. Terraform loads every `.tf` in the dir, so it is split by concern: `versions.tf` (providers), `variables.tf`, `main.tf` (data sources/locals/parameter), `agent.tf` (coder_agent + IDE modules), `container.tf` (workspace container + Traefik routing). |
| `startup.sh.tftpl` | Agent startup script, loaded from `agent.tf` via `templatefile()`. Bash/awk vars use the single-`$` form; Terraform interpolation uses `${...}` and the passed vars map. |
| `Dockerfile` | Optional. When present, the image build workflow builds & pushes it to the local registry. Templates that ship code-server MUST build `FROM computor-code-server:latest` (upstream code-server + the webview service-worker patch, built by `computor.sh` from `docker/code-server-base/` — issue #274), never from `ghcr.io/coder/code-server` directly. |

`template.json` fields:

```json
{
    "coder_template_name": "vscode-workspace",
    "image_name": "computor-workspace-vscode",
    "build_args_env": [],
    "display_name": "VS Code",
    "description": "Shown in the workspace-create UI.",
    "icon": "/icon/code.svg"
}
```

- `coder_template_name` — the name in Coder; what the provision API takes as `template`.
- `image_name` — docker image name, pushed to the local registry as `:latest` + an immutable `:vYYYYMMDD-HHMMSS` tag that the pushed template version pins to.
- `build_args_env` — env var names passed through as docker build args.
- `source_repos` — external git repos the image builds from. Each entry is
  `{"url": ..., "ref": ..., "sha_build_arg": ...}`; before every build the worker resolves `ref`
  to its current commit (`git ls-remote`) and passes it as that build arg.
  **A template that clones a repo must declare it here.** Docker keys a `RUN` layer on its command
  string, so a Dockerfile that checks out a *branch name* is byte-identical on every build: the
  first checkout ever made stays cached and no later commit reaches the image — silently, with the
  build reporting success. The Dockerfile should fetch `${<sha_build_arg>:-${<ref arg>}}` so a bare
  `docker build` still works. An unresolvable repo logs a warning and builds from cache rather than
  failing. The resolved commit is stamped on the image as `computor.extension.revision`, returned by
  the build activity, and shown in the admin panel's progress rows.
- `display_name` / `description` / `icon` — display metadata PATCHed into Coder after each push; the web UI renders these. Icons: Coder built-ins under `/icon/*.svg` (see https://github.com/coder/coder/tree/main/site/static/icon) or an absolute URL.

## Lifecycle

1. `computor.sh up` seeds/syncs `ops/coder/templates/*` into `${SYSTEM_DEPLOYMENT_PATH}/coder/templates/`.
   Deployed dirs containing a `.computor-managed` marker are re-synced from the repo on every
   startup; dirs without the marker are left alone (operator-customized) — delete such a dir once
   to adopt syncing.
2. That directory is bind-mounted into the `coder` server (`/templates`) and the
   `temporal-worker-coder` (`/templates:ro`).
3. `POST /coder/admin/templates/push` (with `build_images: true`) — or backend startup, when Coder
   has no templates yet — runs the Temporal workflow: build image → push to registry →
   `coder templates push` → PATCH TTL + display metadata.
4. `POST /coder/admin/templates/rollout` moves existing workspaces onto the new active version.

## Shared per-user home

All templates mount the **same per-user volume** `coder-home-{owner-uuid}` at `/home/coder`
(every workspace image uses uid 1000, user `coder`). Consequences:

- Files and user-space installs are shared across ALL of a user's workspaces:
  `pip install --user`, virtualenvs/conda in `~`, `npm` prefix in `~`, dotfiles, git config.
- **System (apt) packages are NOT shared and NOT persistent** — they live in the image or the
  container's ephemeral rootfs and are gone after a rebuild/update. Use the personalize hook for
  anything that must survive:
- `~/personalize` — if this executable script exists, every workspace runs it at startup
  (output in `/tmp/personalize.log`). Put `sudo apt-get install -y …` or similar setup there
  (only works while the workspace has root — see "Root and internet policy" below).
- The volume is created by the docker engine on first mount and is **not** managed by
  Terraform, so deleting a workspace never deletes the user's home.
- code-server state is scoped per workspace via `--user-data-dir
  /home/coder/.local/share/code-server-{workspace}` so two running workspaces don't corrupt
  each other's editor state.

### Migrating a pre-shared-home volume

Homes used to be per-workspace (`coder-{workspace-uuid}-home`). Those volumes are left on disk,
detached. To copy one into a user's new shared home:

```bash
# owner uuid = Coder user id (coder users list, or the workspace's coder.owner label)
docker run --rm \
  -v coder-<workspace-uuid>-home:/from \
  -v coder-home-<owner-uuid>:/to \
  alpine sh -c 'cp -a /from/. /to/'
```

## Root and internet policy

Both are **configuration, not image properties** — every template's image ships whatever it
ships (five of the six carry passwordless sudo: `bash`, `ubuntu-desktop`, `vscode` and both
MATLAB images; `jupyter` is the only one without, and has no `sudo` binary at all), and the
container decides whether that sudo can actually be used.

| Knob | Off means | Mechanism |
|---|---|---|
| `allow_root` (default **false**) | `sudo`/`su` refused | `security_opts = ["no-new-privileges:true"]` — the kernel refuses the setuid transition, so one image serves both modes |
| `allow_internet` (default **true**) | no egress | the container is attached to `computor-coder-workspaces-offline` (`internal: true`) instead: no NAT, no default route, so external DNS and connects fail immediately rather than hanging |

Policy comes from two places and is ANDed **inside the template** (`locals` in `main.tf`), so
the weaker input always wins:

- the **template** variables `allow_root` / `allow_internet` — the ceiling, set in the
  workspace template settings and applied as `--variable` at push time;
- the **course** parameters of the same name — narrowing only, delivered as rich parameters at
  provision time and immutable for the life of the workspace.

Both take effect on the next template push plus a workspace rebuild (`POST
/coder/admin/templates/rollout`); a course-level change only affects newly provisioned
workspaces until their next rebuild.

Consequence worth knowing: files a workspace created as root stay root-owned in the shared home
volume, and nothing can repair them once that user's workspaces lose root (the MATLAB templates'
`sudo chown -R coder:coder "$HOME"` self-heal silently no-ops). Sweep `coder-home-*` volumes
before turning root off for users who had it.

## What a workspace can reach

Workspaces sit on their own bridge, whose only other members are the Coder
server and `workspace-ingress`. Everything outbound goes through that proxy's
allowlist (`ops/coder/workspace-ingress/`): the Computor API and git, nothing
else. The platform's web UI, Keycloak, `/docs` and the datastores are
unreachable from a workspace whether or not internet is enabled.

Each workspace app also requires a per-user credential that the ingress
injects (`workspace_app_secret`, plus an argon2 hash for the code-server
templates). Without it, one workspace could drive another directly by
container name — the apps bind `0.0.0.0` on a shared bridge and the names are
predictable. This raises the bar but does not make the bridge a boundary:
workspaces can still see each other's ports.

**Dev only:** a workspace can reach the dev machine through the bridge gateway,
so anything you have listening on `0.0.0.0` there is reachable from inside a
workspace. That is how the dev backend is reached (it runs on the host, not in
a container). Compose binds the platform's own ports to `127.0.0.1`, which is
what keeps the datastores out of reach.

## Adding a new workspace type

1. Copy an existing template dir (`vscode` for editor-based, `bash` for terminal-based,
   `ubuntu-desktop` for GUI-based types).
2. Adjust `template.json` (unique `coder_template_name` + `image_name`, display metadata).
3. Adjust the `Dockerfile` (keep the uid-1000 `coder` user and `/home/coder` home).
4. Adjust the app the agent starts in `startup.sh.tftpl` and the Traefik
   `loadbalancer.server.port` label in `container.tf` to the app's port. Keep the
   ForwardAuth + stripprefix middleware chain and the shared home mount as-is. Apps must
   work behind a stripped path prefix (relative asset/websocket URLs), like ttyd and
   KasmVNC do; code-server needs `--abs-proxy-base-path`. Alternatively, an app that can
   serve under a base path (e.g. JupyterLab's `--ServerApp.base_url`) can own the full
   `/coder/{owner}/{workspace}` prefix — for that template, drop the stripprefix
   middleware so the prefix reaches the container intact (see `jupyter`).
5. Run `computor.sh up` (or copy the dir into the deployed templates dir) and push via
   `POST /coder/admin/templates/push {"templates": ["<dir-name>"], "build_images": true}`.

## MATLAB workspaces

`matlab-vscode` and `matlab-ui` are based on `mathworks/matlab:r2025b` and are
therefore substantially larger and slower to start than the general-purpose
templates. The VS Code variant installs both the Computor extension and the
official MathWorks MATLAB extension; the UI variant serves MathWorks' native
browser interface through MATLAB Proxy.

The MATLAB license is **not** a workspace parameter — there is no control to
fill in when creating a workspace. It is a deployment-wide Terraform variable
(`matlab_license_file`) fed from `MATLAB_MLM_LICENSE_FILE` when the templates
are pushed, so it is set once by the operator and applies to every MATLAB
workspace:

```bash
# .env
MATLAB_MLM_LICENSE_FILE=27000@licenses.example
```

then push the templates again for it to take effect. The value may be a network
license manager (`port@host`) or a license-file path that already exists inside
the container — a host path is **not** mounted automatically. Leave it unset to
use in-browser MathWorks account sign-in.

Because it is pushed from the deployment environment, the variable is **locked**:
`PUT /coder/admin/templates/{name}/settings` rejects attempts to override it.
Treat it as configuration rather than a secret — it is passed through Terraform
and into the container environment, and is readable from inside the workspace.
