---
name: computor-ops
description: Computor infrastructure — docker compose stacks, base images, Coder workspace Terraform templates, Keycloak, Forgejo, nginx/TLS and environment configuration. Use when changing how the stack is built, started, deployed or configured, or when debugging a container, workspace or reverse-proxy problem.
---

# Computor ops

You own `ops/` (compose, coder templates, keycloak, environments, maintenance),
`docker/` (image builds), and the top-level shell entry points.

**Read first:** `docs/development.md`, `docs/architecture.md`, and `ops/docs/`.
Coder template contracts live in each template's own `README.md`.

## Entry points — always these, never raw compose

`./computor.sh up|status|maintenance|update|test`, plus `api.sh` and `web.sh` for
the backend and frontend dev servers. `computor.sh up` builds the base images
first (`computor-base`, `computor-testing-runtimes`) — services build **from**
them, so a raw `docker compose up` silently uses stale bases.

`MATLAB_BASE_IMAGE` is optional: `computor.sh up` builds
`computor-matlab-base:$MATLAB_RELEASE` (release-tagged, **never `:latest`**) and
rebuilds the worker on it.

## Two rules with teeth

**Database isolation.** Main postgres is `computor-postgres` on port **5437**;
Coder postgres is `computor-coder-postgres` on port **5439**. Wipe scripts must
target **only** Coder — `wipe-coder.sh` and `wipe-coder-complete.sh` exist for
that and never touch Postgres/MinIO/Redis. `cmd_down` in `computor.sh` **rejects
`-v`/`--volumes` outright** and points at those scripts; that guard is
deliberate, do not re-enable the flag.

Stop the stack with `./computor.sh down [dev|prod]`, never `docker compose down`
— in prod the public URLs are derived from `PUBLIC_DOMAIN` and left empty in
`.env`, so a bare compose command dies on `${NEXT_PUBLIC_API_URL:?}`.

**No credential defaults.** Write `${SECRET:?must be set in .env}`, never
`${SECRET:-something}`. A default for a credential is how a dev password reaches
production.

## Compose overlays

`docker-compose.base.yaml` plus **either** `.dev.yaml` **or** `.prod.yaml` —
never both; they are mutually exclusive by design. Optional stacks layer on:
`coder`, `matlab`, `keycloak`(`-prod`), `forgejo`(`-keycloak`), `web`, `updater`.

Dev `.env` datastore hosts must be **`localhost`** — container names leak into
`*.tugraz.local` resolution and produce confusing failures. Keycloak in dev is at
the root path.

## Coder workspaces

Templates in `ops/coder/templates/{vscode,bash,ubuntu-desktop,jupyter,matlab-ui,matlab-vscode}/`,
each split into `versions.tf`, `variables.tf`, `main.tf`, `agent.tf`,
`container.tf` + `startup.sh.tftpl`. The contract is in each template's
`README.md` — follow it; the split exists so templates stay diffable.

- **`RUNNING` does not mean usable.** Real readiness is the agent's
  `lifecycle_state` plus a port-wait gate in the startup script. Redirecting on
  `RUNNING` alone sends users into a 502.
- `terraform apply` exiting 1 usually means a same-named container is squatting
  after a lost-track delete — `docker rm -f` it.
- Home volumes are shared per user; a stale root-owned directory aborts the seed
  under `set -e`, hence the self-heal chown in `startup.sh.tftpl`.
- Workspace isolation (root/internet flags, the `internal:true` network swap,
  `workspace-ingress`) is a two-level template⇒course policy AND-ed in Terraform.
  Do not relax one level assuming the other still holds.

## Production

- nginx needs **WebSocket upgrade headers and `http2 on`**. The matlab-ui
  Javascript Desktop is the canary — it fails first when either is missing.
- Prod TLS is HARICA/GEANT and **CRL-only, no OCSP**. `openssl s_client` printing
  "Verify OK" proves nothing about revocation — check the CRL.
- Backend URL config distinguishes `computor_backend_internal` from
  `computor_backend_url`; the DEBUG_MODE pick has an empty-fallback that bites in
  production. Values are pushed via `tasks/temporal_coder_setup.py`.

## Before finishing

`./computor.sh status`, and actually exercise the thing you changed — a container
that starts is not a container that works. Image changes need a rebuild **and** a
restart; figures and the extension live in images, so nothing lands without one.
