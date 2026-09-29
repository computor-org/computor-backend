# Ops Directory Structure

This directory contains all operational configurations and infrastructure files for the Computor platform.

## Directory Layout

```
ops/
├── docker/                     # Docker Compose configurations
│   ├── docker-compose.base.yaml      # Core shared services
│   ├── docker-compose.dev.yaml       # Development-specific
│   ├── docker-compose.prod.yaml      # Production-specific
│   └── docker-compose.*.yaml         # Optional overlays (web, coder, keycloak,
│                                     # forgejo, matlab, updater) — added
│                                     # automatically by computor.sh from .env flags
│
├── environments/              # Environment configuration template
│   └── .env.common.template   # All variables; setup-env.sh generates .env from it
│
├── keycloak/                  # IdP registration one-shot (stdlib-only python),
│                              # mounted by docker-compose.keycloak.yaml; plus
│                              # setup_terms.py (computor.at only, see below)
│
├── lib/                       # Shared bash library for ./computor.sh
│   ├── common.sh              # env loading, COMPOSE_FILES assembly, maintenance
│   └── update.sh              # self-update executor (see docs/SELF_UPDATE.md)
│
└── docs/                      # Operational documentation
    ├── DOCKER_SETUP.md        # Complete Docker setup guide
    ├── ENV_CONFIGURATION.md   # Environment variables reference
    ├── CODER_INTEGRATION.md   # Coder workspace integration
    ├── REVERSE_PROXY.md       # nginx (TLS) → Traefik production setup
    └── SELF_UPDATE.md         # One-click updates from the admin UI / CLI
```

## Quick Reference

### Starting Services

From the project root directory:

```bash
# Development
./computor.sh up dev -d

# Production
./computor.sh up prod -d

# Stop / status / maintenance / self-update
./computor.sh down
./computor.sh status
./computor.sh maintenance enter prod     # static maintenance page, services stopped
./computor.sh update check               # see docs/SELF_UPDATE.md

# Optional services are .env flags: CODER_ENABLED, KEYCLOAK_ENABLED,
# GIT_SERVER=forgejo, MATLAB_ENABLED, UPDATE_ENABLED
```

### Environment Setup

From the project root directory:

```bash
# Interactive setup
./setup-env.sh

# Automated setup with defaults
./setup-env.sh --auto

# Force overwrite existing configs
./setup-env.sh --force
```

### Direct Docker Compose Usage

Avoid raw `docker compose` for lifecycle operations: the overlay list depends on the
`.env` feature flags, and in prod the public URLs are derived from `PUBLIC_DOMAIN` at
launch — a bare compose command fails interpolation. `./computor.sh` (via
`ops/lib/common.sh`) handles both. For ad-hoc read-only commands (logs, ps), reuse the
assembled file list:

```bash
source ops/lib/common.sh
load_env && derive_public_urls dev && pin_project_name && assemble_compose_files dev
docker compose $COMPOSE_FILES logs -f [service-name]
```

## Environment Files

The runtime scripts read a single `.env` in the project root. `./setup-env.sh` creates it:

- `.env.common` - Generated template with ALL variables and freshly generated secrets
- `.env` - Copied from `.env.common` (an existing `.env` is never overwritten)

`ops/environments/.env.common.template` is the static reference template behind
`setup-env.sh`; dev vs. prod is a runtime argument (`./computor.sh up dev|prod`), not a
separate env file.

## Key Services

### Core Services (base.yaml)
- PostgreSQL (main database)
- Redis (cache)
- Temporal + PostgreSQL (workflows)
- MinIO (object storage)
- Traefik (reverse proxy)

### Development Services (dev.yaml)
- Temporal UI
- Development workers
- Optional Keycloak SSO

### Production Services (prod.yaml)
- Uvicorn API server
- Frontend application
- Production workers

### Coder Services (coder.yaml)
- Coder server
- Docker registry
- Workspace builders
- Template provisioning

## Legal profile and Keycloak terms (per deployment)

The web build bakes in `NEXT_PUBLIC_LEGAL_PROFILE` (set it in `.env` before
`computor.sh` builds the web image):

| Deployment | `NEXT_PUBLIC_LEGAL_PROFILE` | Effect |
|---|---|---|
| computor.at | `computor-at` | Own pages `/impressum`, `/privacy`, `/terms`, `/accessibility`, `/report` (from `computor-web/content/legal/`), footer links to them |
| code.tugraz.at | `tugraz-internal` | Footer links to TU Graz's Impressum, Datenschutzerklärung and Barrierefreiheitserklärung; no own legal pages |
| any other install | `none` (default) | No legal links, legal routes return 404 |

`ops/keycloak/setup_terms.py` makes the Keycloak required action "Terms and
Conditions" a default action in realm `computor` and sets the realm
localization texts `termsTitle`/`termsText`/`doAccept`/`doDecline` (de, en)
from `ops/keycloak/computor-at-terms.json`. It is idempotent (reads first,
writes only differences; a second run reports 0 changes).

**Run it for computor.at only.** Never run it for code.tugraz.at: that
instance is covered by TU Graz's own terms and must not ask users to accept
computor.at's. The script refuses to run unless `COMPUTOR_LEGAL_PROFILE=computor-at`
is set. On the computor.at host, from the repository root:

```bash
# Preview, then apply (Keycloak URL and admin credentials come from .env)
docker run --rm --network computor-network --env-file .env \
  -e COMPUTOR_LEGAL_PROFILE=computor-at \
  -v "$PWD/ops/keycloak:/kc:ro" python:3.13-slim \
  python3 /kc/setup_terms.py --dry-run
# ...same command without --dry-run to apply.
# Existing accounts are not gated by a default action; to ask them once too:
#   python3 /kc/setup_terms.py --require-for-existing-users
```

After applying, verify on staging that the GitHub first-broker-login flow shows
the terms page before any token is issued. For a new terms version, update
`computor-at-terms.json` and the texts in `computor-web/content/legal/`, then
run with `--require-for-existing-users` after clearing the users'
`terms_and_conditions` attribute.

## Notes

- The lifecycle CLI (`computor.sh`) and the `.env` scaffolding script (`setup-env.sh`)
  live in the project root
- The `.env` file is created in the project root, not in ops/
- All Docker Compose files use relative paths from the project root
- The `docker/postgres-init/` directory in the project root contains database initialization scripts