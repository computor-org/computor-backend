# Computor integration tests

Full-stack integration tests for the Computor platform. They spin up the
backend, Temporal, Postgres, Redis, MinIO, and a **real GitLab CE** in
Docker, then drive the system end-to-end against that stack.

> Tracked in [issue #106](https://github.com/computor-org/computor-backend/issues/106).
> Milestones M1–M8 live on branch `feat/integration-tests`.

## Run semantics

These tests run like a real user session: **no rollbacks, no per-test
reset**. The stack comes up once, tests accumulate state, assertions look
at final state, and teardown is a volume wipe. Tests should therefore be
written as a coherent story. Entities that need isolation should carry a
unique suffix (uuid/test-id) in their path.

## Prerequisites

- Docker + Docker Compose v2 (`docker compose`)
- Python 3.10+
- Free host ports: `8085`, `8444`, `2224` (GitLab) and the `1xxxx` range
  used by the infra services (see `.env.integration.template`). Tweak in
  `.env.integration` if any collide.

## First-time setup

```bash
cd integration-tests
make env               # creates .env.integration from the template
pip install -e .       # installs pytest + deps (ideally in a venv)
```

## Running the stack

```bash
make up                # build + start + wait for health + bootstrap GitLab PAT
make test              # run the pytest suite
make down              # stop containers, keep volumes
make clean             # stop containers and wipe volumes
```

GitLab takes ~3–5 minutes to boot cold. `make up` waits on the healthcheck
and then calls `scripts/bootstrap_gitlab.py` to mint an admin PAT and
write it back into `.env.integration` as `GITLAB_ADMIN_TOKEN`.

Useful while developing:

```bash
make logs              # tail all logs
make ps                # show container status
make shell-api         # bash into the API container
make shell-gitlab      # bash into the GitLab container
```

## Layout

```
integration-tests/
├── docker-compose.integration.yaml   # self-contained stack incl. GitLab
├── .env.integration.template
├── Makefile
├── conftest.py                       # top-level fixtures
├── pyproject.toml
├── fixtures/                         # per-topic fixtures (gitlab, api, db, users, ...)
├── helpers/                          # reusable assertions / workflow polling
├── data/                             # dummy deployment configs, dummy users
├── scripts/
│   ├── wait_for_services.sh
│   └── bootstrap_gitlab.py
└── suites/
    ├── 01_smoke/                     # services reachable
    ├── 02_auth/                      # login / tokens
    ├── 03_permissions/               # RBAC matrix: endpoint × role → expected status
    ├── 04_deployment/                # org → family → course via Temporal
    ├── 05_examples/                  # upload / assign examples
    ├── 06_release/                   # lecturer release → student-template repo
    ├── 07_student_workflow/          # student fork / submission / testing
    └── 08_full_lifecycle/            # golden-path e2e
```

## Scope

In scope for this suite: API + Temporal + Postgres + Redis + MinIO + GitLab.

Out of scope (deliberately excluded from the compose stack):
- MATLAB testing worker (licensed; excluded intentionally).
- Coder workspace services (huge surface area; would blow up test runtime).
  `CODER_ENABLED=false` is hard-wired on the API container.
- `computor-web` (Next.js) UI tests.
- VSCode extension (`/Users/theta/computor/computor-vsc-extension`) —
  will be pulled into this monorepo later.
