# QA stack

`qactl.sh` runs one isolated Computor stack for end-to-end QA
([computor-org/issues#529](https://github.com/computor-org/issues/issues/529)):
web, API, workers, Keycloak 26 with computor.at's signup policy, Forgejo, Coder
with the VS Code workspace, and [Mailpit](https://mailpit.axllent.org/) as the
only mailbox. It reuses the production and preview compose files and adds
`docker-compose.qa.yaml`.

Isolation on a shared host: Compose project `qa`, containers `qa-*`, images
`qa-*`, networks `qa-computor-network`, `qa-coder-workspaces` and
`qa-coder-workspaces-offline`, state under `QA_HOME`
(default `/mnt/storage/computor-qa`), every port on 127.0.0.1, CPU and memory
limits on every service (ceilings that add up to about 28 CPUs and 28 GiB; an
idle stack uses about 0.3 CPU and 2.2 GiB, plus each running workspace). Two things are shared with the host: Coder's
workspace registry must listen on `localhost:5000` (the templates hardcode it),
and workspace images build `FROM computor-code-server:latest`, which `qactl`
rebuilds only when its inputs change, as `computor.sh` does.

## Commands

Run from a checkout of this repository on the QA host (Docker, `python3`,
`openssl`, `envsubst`):

```bash
ops/qa/qactl.sh up       # create state if missing, build, start, seed
ops/qa/qactl.sh status   # containers, deployed refs, URLs, tunnel command
ops/qa/qactl.sh tunnel   # ssh command for your laptop
ops/qa/qactl.sh down     # stop, keep state
ops/qa/qactl.sh reset    # wipe all state and start again from the synthetic baseline
ops/qa/qactl.sh seed [baseline|content|templates|returning]   # re-apply all or one step
ops/qa/qactl.sh compose logs -f uvicorn
```

`deploy` changes what runs. Options combine; `--content-ref` also resets all state:

```bash
ops/qa/qactl.sh deploy --backend-ref origin/my-branch   # API, workers and web from that ref
ops/qa/qactl.sh deploy --vsix ~/computor-2027.3.7.vsix   # workspace image with that extension
ops/qa/qactl.sh deploy --content-ref my-branch           # data-science-python courses from that ref
```

A backend ref is checked out in the detached worktree `QA_HOME/src/backend`
(created from the main checkout, `QA_BACKEND_REPO`) and its images are rebuilt.
The VSIX replaces the template's git build of the extension in the deployed
template copy only, and every version in the instance's extension registry is
yanked, so workspaces keep that VSIX instead of updating to the approved one;
running workspaces get it at their next start; `--vsix none` returns to the
git build. A content ref is downloaded as
a GitHub archive and imported into a fresh baseline (`reset`): examples through
the examples API, courses through `deploy-course`, then released like the
lecturer tools do. The public mirror has no instructor block in most
`meta.yaml` files, so the import adds `studentSubmissionFiles` from the file
names the exercise text asks for; there are no tests, so a real test run ends
in an error.

## What a fresh stack contains

- **New learner**: nobody. Register through the Keycloak form; the
  verification mail lands in Mailpit (`GET /api/v1/search?query=to:"…"`,
  `GET /api/v1/message/<ID>`). Email verification is on, so the password is
  set after the link, as on computor.at
  ([computor-org/issues#441](https://github.com/computor-org/issues/issues/441)).
- **Returning learner** `qa-returning@example.com`: enrolled in *Data Science
  mit Python – Grundlagen*, results on the first assignments of week 1 (one at
  0 %), the next assignment open, and a stopped workspace.
- **Lecturer** `qa-lecturer@example.com` and **admin** `qa-admin@example.com`.
- The three *Data Science mit Python* courses, public in the catalog.

Passwords and API tokens are generated per stack and kept in
`QA_HOME/credentials.env` (mode 0600), never in git.

## Smoke runs

`smoke/new-learner.mjs` registers a new learner through the UI, follows the
verification mail, joins Grundlagen and opens the workspace until VS Code shows
the Computor extension, saving a screenshot per step. Run it headless on the
host, or on a laptop through the tunnel, with any Playwright install:

```bash
QA_ORIGIN=http://localhost:18480 QA_MAILPIT=http://127.0.0.1:18425 \
QA_SCREENS=/tmp/qa-screens QA_PLAYWRIGHT_FROM=/path/to/dir/with/node_modules \
node ops/qa/smoke/new-learner.mjs
```

`smoke/returning-learner.mjs` signs in as the returning learner
(`QA_RETURNING_EMAIL`, `QA_RETURNING_PASSWORD` from the credentials file) and
saves the dashboard, the workspace list and the course page.

## Nightly runs

Scheduling belongs in computor-infra. A nightly job needs: a checkout of this
repository on the QA host, `ops/qa/qactl.sh reset` (or `deploy` with the refs
under test), the smoke run above with a Playwright install, and somewhere to
keep the screenshots. It must not run while another job uses port 5000.
