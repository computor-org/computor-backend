# Computor integration tests

Full-stack integration tests for the Computor platform. They spin up the
backend, Temporal, Postgres, Redis, and MinIO in Docker, then drive the
system end-to-end against that stack over HTTP.

> **Status / roadmap:** this harness is being rebuilt per
> [`testing-strategy/`](../testing-strategy/README.md). GitLab has been
> removed entirely (the platform is Forgejo-only); **Keycloak and Forgejo
> join the stack with backlog phase P1**, which also restores authentication
> (the backend dropped local password login — auth suites need Keycloak to
> run). Until P1 lands, only the smoke suite is meaningful.

## Run semantics

These tests run like a real user session: **no rollbacks, no per-test
reset**. The stack comes up once, tests accumulate state, assertions look
at final state, and teardown is a volume wipe. Tests should therefore be
written as a coherent story. Entities that need isolation should carry a
unique suffix (uuid/test-id) in their path.

## Prerequisites

- Docker + Docker Compose v2 (`docker compose`)
- Python 3.10+
- Free host ports in the `1xxxx` range used by the infra services (see
  `.env.integration.template`). Tweak in `.env.integration` if any collide.

## First-time setup

```bash
cd integration-tests
make env               # creates .env.integration from the template
pip install -e .       # installs pytest + deps (ideally in a venv)
```

## Running the stack

```bash
make up                # build + start + wait for health
make test              # run the pytest suite
make down              # stop containers, keep volumes
make clean             # stop containers and wipe volumes (full reset)
```

Useful while developing:

```bash
make logs              # tail all logs
make ps                # show container status
make shell-api         # bash into the API container
```

## Layout

```
integration-tests/
├── docker-compose.integration.yaml   # self-contained stack
├── .env.integration.template
├── Makefile
├── conftest.py                       # top-level fixtures
├── pyproject.toml
├── fixtures/                         # per-topic fixtures (api, db, users, clients, matrix)
├── helpers/                          # shared assertion helpers (built out in P4)
├── scripts/
│   └── wait_for_services.sh
└── suites/
    ├── 01_smoke/                     # services reachable
    ├── 02_auth/                      # SSO login / tokens / invites
    ├── 03_permissions/               # RBAC matrix: endpoint × role → expected status
    ├── 05_examples/                  # upload / assign examples
    ├── 06_release/                   # lecturer release → student-template repo
    ├── 07_student_workflow/          # repo provisioning / submission / testing
    └── 08_full_lifecycle/            # tutor grading, golden-path e2e
```

(`04_contracts/` — payload validation & error contracts — is planned; it
replaces the removed GitLab deployment suite. See
`testing-strategy/06-integration-suites.md`.)

## Scope

In scope: API + Temporal + Postgres + Redis + MinIO (+ Keycloak and
Forgejo once P1 lands).

Out of scope (deliberately excluded from the compose stack):
- GitLab — the platform is Forgejo-only; GitLab-managed repositories are
  not tested anywhere.
- MATLAB testing worker (licensed; excluded intentionally).
- Coder workspace services (excluded by policy).
  `CODER_ENABLED=false` is hard-wired on the API container.
- `computor-web` (Next.js) — covered by its own Playwright suite
  (`computor-web/e2e/`).
- VSCode extension (separate repo `computor-vsc-extension`).
