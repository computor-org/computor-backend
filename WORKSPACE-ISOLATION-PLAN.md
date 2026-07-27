# Workspace isolation modes — implementation plan

**Branch:** `feat/workspace-isolation-modes` off `release/2026.10`

> Approved 2026-07-27. Phase order is deliberate — Phase 1 is shippable on its own. Phase 3 was
> later reworked from a public-domain alias onto internal names (see Design) to remove the
> production-certificate handling it would otherwise have required.

---

## Context

Coder workspaces grant passwordless root today, and it is baked into the Docker images
(`bash`, `ubuntu-desktop`, `vscode` and both MATLAB images; only `jupyter` has no `sudo`).
Requirements changed: root must be a **configuration** decision, not an image property, without
maintaining a second image per workspace type. Alongside it:

- workspaces must reach the **backend API and Forgejo over the docker network**, not over the
  public internet-facing URL (matters now for the VS Code extension, later for every type);
- **internet access must be switchable**, configurable from the web UI — per template in the
  workspaces admin tab, and per course in course workspaces;
- a workspace must reach **nothing else** — no postgres, redis, minio, keycloak, temporal.

Investigation (2026-07-27, measured against the dev stack) turned up two pre-existing holes that
make the naive version of this impossible:

1. **Traefik sits on the workspace bridge and routes by bare `PathPrefix`.** From a workspace,
   `http://traefik/docs` → **200, unauthenticated**. In prod that table also carries `/api`, `/`,
   `/auth`, `/forgejo`. An `internal: true` network alone could therefore never mean
   "backend + git only".
2. **Workspace ↔ workspace is wide open.** All workspaces share one bridge and every app is
   unauthenticated behind Traefik's ForwardAuth (`code-server --auth none`, `ttyd --writable`,
   KasmVNC `-disableBasicAuth`, Jupyter with empty token *and* password). Verified live:
   `curl http://coder-alice-terminal:7681/` → 200 with an interactive root shell.

Intended outcome: root and internet become per-template/per-course policy; offline workspaces
reach exactly the backend and git; and one workspace can no longer drive another.

### Verified mechanics the plan relies on

| Fact | Evidence |
|---|---|
| `security_opts = ["no-new-privileges:true"]` kills sudo, kernel-enforced | `sudo` → *"no new privileges flag is set"*, `su` → auth failure, `apt-get` → exit 100 |
| The apps survive it | XFCE+KasmVNC ready in 1s, ttyd 1s, code-server 2s |
| `internal: true` kills egress with **no default route** | DNS/curl/apt fail in 0s — no hangs |
| Container DNS still works on an internal net | dual-homed service reached by name → 200 |
| Dual-homing restores egress | ⇒ the toggle must **swap** the network, never add one |
| Cross-bridge isolation holds | workspace-net → `computor-network` IP: blocked |
| `url.<x>.insteadOf` cannot repoint git | the extension embeds `user:token@` in the clone URL (`addTokenToGitUrl` → `execGitClone`), and git prefix-matches the URL as written |

---

## Design

**Two-level policy.** The template setting is a ceiling; the course setting narrows it. The AND is
evaluated **inside Terraform** so a stray rich parameter can never widen access:

```hcl
locals {
  root_enabled     = var.allow_root     && data.coder_parameter.allow_root.value
  internet_enabled = var.allow_internet && data.coder_parameter.allow_internet.value
}
```

Both parameters default to `true` ("no course-level restriction") and are `mutable = false`, like
`home_mode`. Template values arrive as `--variable` at push time; course values as rich parameters
per workspace.

**Internal-name ingress.** A `workspace-ingress` proxy answers to `computor-api` and
`computor-git` on the workspace networks and carries an allowlist route table. Nothing else the
platform serves has a name a workspace can resolve.

This replaces an earlier split-horizon design that aliased the proxy as `PUBLIC_DOMAIN` so public
URLs would keep working verbatim. That needed no code changes, but it moved the workspace's TLS
handshake onto the proxy instead of nginx — so it required a copy of the production certificate
inside the container plus a restart hook on every renewal. Permanent operational handwork to avoid
a one-time code change was the wrong trade. Internal names are plain HTTP, so no certificate has to
exist anywhere. The cost is that clone URLs are rendered per audience, and clones made before the
switch keep a remote the workspace can no longer resolve.

**Per-user app secret.** Each *user* (not workspace — `/home/coder` is one shared volume and
KasmVNC's `~/.kasmpasswd` would collide between two of their running desktops) gets a secret that
the ingress injects as a request header, and that each app requires.

---

## Phase 1 — template mechanics

`ops/docker/docker-compose.coder.yaml` — add the offline network:

```yaml
networks:
  computor-coder-workspaces-offline:
    name: computor-coder-workspaces-offline
    internal: true
```

Every template dir (`bash`, `ubuntu-desktop`, `vscode`, `jupyter`, `matlab-ui`, `matlab-vscode`) —
same pattern in each:

- `variables.tf`: `allow_root` (bool, **default `false`**), `allow_internet` (bool, default `true`),
  `docker_network_offline` (string).
- `main.tf`: two `data "coder_parameter"` blocks beside the existing `home_mode` one
  (`mutable = false`, default `true`), plus the `locals` above.
- `container.tf`: `security_opts = local.root_enabled ? [] : ["no-new-privileges:true"]`;
  `networks_advanced { name = local.ws_net }` where
  `ws_net = local.internet_enabled ? var.docker_network : var.docker_network_offline` — and the
  `traefik.docker.network` label must use `local.ws_net`, not `var.docker_network`.

`ops/coder/templates/README.md` — document both knobs; fix line 60, which wrongly claims only the
desktop image has sudo.

Gotchas: `temporal_coder_setup.py:449` skips falsy override values, so the safe state must be the
variable's default (it is); `"false"` is a non-empty string and passes fine. MATLAB's
`startup.sh.tftpl:13` self-heal `sudo chown -R coder:coder $HOME` silently no-ops without root —
sweep root-owned files out of `coder-home-*` volumes before flipping those templates.

## Phase 2 — configuration surfaces

Mirror the existing `memory_mb` / `cpu_shares` path end to end.

**DB** — `computor-backend/src/computor_backend/model/workspace.py` + an alembic revision modelled
on `b9c8d7e6f5a4_add_workspace_template_settings.py`:

- `workspace_template_settings`: `allow_root BOOLEAN NOT NULL DEFAULT false`,
  `allow_internet BOOLEAN NOT NULL DEFAULT true` — the ceiling.
- `course_workspace_template`: `allow_root BOOLEAN NULL`, `allow_internet BOOLEAN NULL` —
  NULL means inherit.

**Backend** (`computor-backend/src/computor_backend/`):

- `api/coder.py:_per_template_variables()` (line 852) — emit both columns as `--variable`, exactly
  as the resource caps are emitted.
- `api/coder.py:_PUSH_MANAGED_VARIABLES` (~line 180) — add both names so they cannot *also* be set
  as raw variable overrides and silently conflict; `_settings_row_to_schema` (1020) gains the fields.
- `api/coder.py:provision_workspace` (308) and
  `business_logic/course_workspaces.py:provision_student_workspaces` (435) — resolve the effective
  policy (reuse `template_settings_row`, `course_workspaces.py:76`) and pass it down; both already
  funnel into `client.provision_workspace(...)`, so extend that signature
  (`coder/client.py:1297`) alongside `home_mode`.
- `coder/client.py:create_workspace` (803) — send the rich parameters, **and re-send them in
  `update_workspace_token` (1150) and `update_workspace_to_version` (1231)**: omitted rich
  parameters reset to their default, the footgun `home_mode` already works around via
  `_get_build_param` (1199).

**DTOs — `computor-types`, never backend modules:** `coder.py`
(`WorkspaceTemplateSettingsSchema`/`Update`, `CoderWorkspaceCreate`) and `course_workspaces.py`
(`CourseWorkspaceTemplateItem`, `CourseWorkspaceSettingsGet`/`Update`, nullable).

**Web** (`computor-web`, **yarn** — the generated client is stale, edit surgically and validate
with `npx tsc --noEmit`):

- `src/components/workspaces/TemplateSettingsPanel.tsx` — two first-class switches beside the
  resource limits, not raw variable rows; copy states the change lands at the next template push.
- `app/workspaces/admin/courses/[courseId]/page.tsx` — per-template policy on the existing
  allowed-templates rows; a course can only narrow, so show the ceiling and disable the control
  when it is already `false`.
- `app/courses/[id]/lecturer/workspaces/page.tsx` — effective policy read-only, so a lecturer
  bulk-provisioning can see what students will get.
- `src/types/workspaces.ts` — matching fields.

## Phase 3 — split-horizon ingress

New `workspace-ingress` service in `ops/docker/docker-compose.coder.yaml` (traefik:v3.6.6):

- networks `computor-network` + both workspace networks, with `aliases: [${PUBLIC_DOMAIN}]` on the
  workspace side; entrypoints `websecure :443` (host TLS cert mounted read-only) and `web :80`;
- docker provider scoped by `--providers.docker.constraints=Label("computor.ingress","workspace")`
  so it picks up the Traefik labels workspace containers already carry — ForwardAuth and
  stripprefix keep working untouched; prod goes through the existing `socket-proxy`;
- file provider allowlist: `/api` → `uvicorn:8000`, `/forgejo` → `forgejo:3030` (both stripprefix),
  everything else → 403.

Main traefik (`docker-compose.dev.yaml:9-13`, `docker-compose.prod.yaml:33-41`): inverse constraint
`!Label("computor.ingress","workspace")`, drop `computor-coder-workspaces` from its networks
(`docker-compose.coder.yaml:14-16`), add a `/coder` router pointing at workspace-ingress.
Workspace `container.tf` gains the `computor.ingress=workspace` label.

Net effect: workspace-net members become `{coder, workspace-ingress}`; uvicorn and forgejo stay on
`computor-network`, reachable only through the proxy's route table.

**Dev parity** — dev's URLs (`host.docker.internal:8000`, `localhost:3030`) cannot carry a network
alias, so give dev a real name: map `computor.dev.test` → `127.0.0.1` in the dev machine's
`/etc/hosts` (reserved TLD; **not** `.local` (mDNS) and not the host resolver, which wildcards
unknown names to `127.10.10.10`), set `BACKEND_EXTERNAL_URL`/`GIT_SERVER_URL` to it via port 8080,
and `FORGEJO_TRAEFIK_ENABLED=true` so `/forgejo` is actually routed. In dev the proxy's `/api`
route targets `host.docker.internal:8000`.

## Phase 4 — per-user app auth

Derive the secret deterministically — no migration, nothing at rest: HMAC of the user id under
`TOKEN_SECRET`, reusing `utils/encryption.py:_token_secret()` (line 17); mint it next to
`coder/service.py:mint_workspace_token` (21) and pass it through `provision_workspace` as a rich
parameter.

The ingress injects it per workspace router (labels are already rendered per container):

```hcl
labels {
  label = "traefik.http.middlewares.appauth-${owner}-${ws}.headers.customrequestheaders.Authorization"
  value = "Basic ${base64encode("coder:${local.app_secret}")}"
}
# chain order: auth-…, appauth-…, strip-…
```

| Template | App-side change |
|---|---|
| `bash` | `ttyd --credential coder:$SECRET` |
| `ubuntu-desktop` | drop `-disableBasicAuth`; seed `~/.kasmpasswd` from the secret instead of the random one |
| `jupyter` | `--IdentityProvider.token=$SECRET`, injected as `Authorization: token …` |
| `vscode` | `--auth password` with `PASSWORD=$SECRET` — **gated on the spike below** |

**Spike, do this first:** code-server validates a session cookie, not `Authorization`. Pre-compute
the hash it expects, inject `Cookie: key=…`, and confirm the pinned version accepts it without the
login page and without clobbering other cookies. If it fails, fall back to a one-time password
surfaced in the launch flow (a visible UX regression on the most-used template) — or reopen serving
apps through Coder's own proxy, which removes the whole class.

**Cleanup in the same pass:** `code_server_password` is declared as a *Terraform variable*
(`vscode/variables.tf:47`, deployment-wide) while `coder/client.py:833-837` sends it as a *rich
parameter* the template never declares — dead and latently broken. Remove that path and the stale
`computor-web/src/types/workspaces.ts:110` field.

This raises the bar; it does not make the bridge a boundary — workspaces can still port-scan each
other.

## Phase 5 — hardening

- **Forgejo migration egress bypass:** Forgejo stays reachable offline, and `/repos/migrate` (which
  the platform itself uses for student repos) fetches arbitrary external URLs on the user's behalf.
  Set `[migrations] ALLOW_LOCALNETWORK=false` + an `ALLOWED_DOMAINS` allowlist, or "offline" is
  bypassable.
- **`/docs` is unauthenticated** to anyone who can reach Traefik — every workspace and every browser
  on the public domain (`docker-compose.base.yaml:219-225`, no ForwardAuth). Confirm intent; add
  the auth middleware if not.
- **Dev host exposure:** a dev workspace reaches the bridge gateway, so anything on the dev machine
  bound to `0.0.0.0` is reachable (verified: backend `:8000`, web `:3000`; forgejo and postgres are
  safe only because compose binds them to `127.0.0.1`). Document it.

---

## Verification

**Policy matrix** (Phases 1–2) — for one template, all four combinations:

| template | course | expected |
|---|---|---|
| root off | root on | no root (ceiling wins) |
| root on | root off | no root |
| root on | inherit (null) | root |
| internet off | internet on | no internet |

In-workspace: `sudo id` refused; `apt-get install` exits 100 immediately; `curl https://github.com`
fails in 0s with no default route; XFCE / ttyd / code-server still reach `lifecycle_state=ready`.

**Phase 3** — from an offline workspace: `https://PUBLIC_DOMAIN/api/...` → 200; `git clone` of a
real student repo with its unchanged token URL succeeds; `https://PUBLIC_DOMAIN/`, `/auth`, `/docs`
→ 403; postgres/redis/minio/temporal unreachable; `coder:7080` still reachable (the agent must
connect). Online workspace: unchanged behaviour.

**Phase 4** — re-run the investigation's live repro: start two containers on the workspace bridge
and `curl http://coder-<other>-<ws>:7681/`; it must return 401 instead of a terminal. Then confirm
the browser path still opens each of the four templates without a credential prompt.

**Regression** — backend unit suite against a HEAD worktree (baseline on `release/2026.10`:
134 failed / 904 passed / 20 skipped / 25 errors, plus the two collection errors that must be
`--ignore`d — measure the delta, never the absolute); `npx tsc --noEmit` in `computor-web`;
`computor.sh up` clean start; existing workspaces roll onto the new template versions via
`POST /coder/admin/templates/rollout` without losing their homes.

## Risks / open items

1. ~~Prod TLS cert path~~ — resolved by dropping TLS: workspaces use internal names over plain
   HTTP, so no certificate has to be placed or renewed anywhere.
2. ~~code-server cookie injection~~ — spike done: code-server compares its session cookie against
   HASHED_PASSWORD, so the ingress injects the argon2 hash and no login page appears.
3. **Rollout timing** — template changes need a push + rollout; course changes only affect newly
   provisioned workspaces until a rebuild. Say so in the UI copy.
4. **`allow_root=false` is a behaviour change** for bash / ubuntu-desktop / vscode / MATLAB at the
   next push. Announce it; sweep root-owned files from shared homes first.

## Out of scope

Serving workspace apps through Coder's own proxy (`coder_app`), per-workspace docker networks, and
the GitLab-era provisioning path.
