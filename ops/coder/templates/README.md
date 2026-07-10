# Coder Workspace Templates

Each subdirectory is one workspace type. Templates are discovered, built and
pushed automatically — there is no registration list in code.

## Template contract

A template directory must contain:

| File | Purpose |
|---|---|
| `template.json` | Manifest (see below). Its presence makes the directory a template. |
| `main.tf` | Coder Terraform template: agent, workspace container, Traefik routing. |
| `Dockerfile` | Optional. When present, the image build workflow builds & pushes it to the local registry. |

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
- `display_name` / `description` / `icon` — display metadata PATCHed into Coder after each push; the web UI renders these. Icons: Coder built-ins under `/icon/*.svg` (see https://github.com/coder/coder/tree/main/site/static/icon) or an absolute URL.

## Lifecycle

1. `startup.sh` seeds/syncs `ops/coder/templates/*` into `${SYSTEM_DEPLOYMENT_PATH}/coder/templates/`.
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
  (only in images whose user has sudo; the desktop image does, the others do not).
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

## Adding a new workspace type

1. Copy an existing template dir (`vscode` for editor-based, `bash` for terminal-based,
   `ubuntu-desktop` for GUI-based types).
2. Adjust `template.json` (unique `coder_template_name` + `image_name`, display metadata).
3. Adjust the `Dockerfile` (keep the uid-1000 `coder` user and `/home/coder` home).
4. In `main.tf` adjust the app the agent starts and the Traefik
   `loadbalancer.server.port` label to the app's port. Keep the ForwardAuth + stripprefix
   middleware chain and the shared home mount as-is. Apps must work behind a stripped path
   prefix (relative asset/websocket URLs), like ttyd and KasmVNC do; code-server needs
   `--abs-proxy-base-path`.
5. Run `startup.sh` (or copy the dir into the deployed templates dir) and push via
   `POST /coder/admin/templates/push {"templates": ["<dir-name>"], "build_images": true}`.
