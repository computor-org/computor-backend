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

`deploy` changes what runs. `--backend-ref` and `--vsix` preserve learner state.
Either `--content-ref` or `--examples` wipes **all QA state** and imports a fresh
synthetic baseline, including when combined with the other options:

```bash
ops/qa/qactl.sh deploy --backend-ref origin/my-branch   # API, workers and web from that ref
ops/qa/qactl.sh deploy --vsix ~/computor-2027.3.7.vsix   # workspace image with that extension
ops/qa/qactl.sh deploy --content-ref my-branch           # RESET ALL STATE; import courses
ops/qa/qactl.sh deploy --examples /mnt/storage/computor-qa-inputs/examples-<commit>.tar.gz # RESET ALL STATE
ops/qa/qactl.sh reader --content-ref my-branch           # /learn reader pinned to that mirror ref
```

A backend ref is checked out in the detached worktree `QA_HOME/src/backend`
(created from the main checkout, `QA_BACKEND_REPO`) and its images are rebuilt.
The VSIX replaces the template's git build of the extension in the deployed
template copy only, and every version in the instance's extension registry is
yanked, so workspaces keep that VSIX instead of updating to the approved one;
running workspaces get it at their next start; `--vsix none` returns to the
git build.

On `up` and state-preserving `deploy`, the controller hashes theme paths and
bytes from the mounted backend checkout. If an existing Keycloak process has
not acknowledged that digest, only QA Keycloak restarts to clear its theme
metadata cache. Newly created containers already load the current theme and
need no extra restart. The digest is recorded atomically only after Keycloak
is healthy. An existing stack without a digest refreshes once rather than
marking potentially stale cached metadata as current. This preserves Keycloak's
database, users and persistent QA state. Ordinary session expiry still applies;
uninterrupted active sessions are not guaranteed.

The content and examples refs shown by `status` identify the baseline imports.
They do not track later lecturer edits or uploads. Record the actual course
manifest, example versions and their source revisions separately when rehearsing
an update.

## Course content

The stack gets its content the way computor.at does. The runnable examples
(exercise texts, `test.yaml`, `localTests` with reference solutions and the
full `meta.yaml`) live in the private GitLab repository
`codeability/development/examples` under `python/`. The public mirror
[data-science-python](https://github.com/computor-org/data-science-python)
has the text-only examples, the course manifests `courses/python-*.yaml` and
the snapshot behind the `/learn` reader. The examples are uploaded through the
examples API, the courses through `deploy-course`, and both are released like
the lecturer tools do.

The QA host has no GitLab credentials. Fetch the package where `glab` is
signed in to gitlab.tugraz.at and copy only the archive:

```bash
QA_INPUTS=~/qa-inputs ops/qa/fetch_examples.sh main mailuefterl:/mnt/storage/computor-qa-inputs
# writes examples-<commit12>.tar.gz (for qactl) and examples-<commit12>.zip (for the web upload)
```

Without `--examples` the stack falls back to the mirror's examples, adds
`studentSubmissionFiles` from the file names the exercise text asks for, and
every test run ends in an error.

`qactl.sh reader --content-ref REF` does what publishing a mirror revision on
computor.at takes: it pins `computor-web/learning-source.json` in the deployed
worktree to that commit, rebuilds and restarts the web. A later
`deploy --backend-ref` drops the pin.

## What a fresh stack contains

- **New learner**: nobody. Register through the Keycloak form; the
  verification mail lands in Mailpit (`GET /api/v1/search?query=to:"…"`,
  `GET /api/v1/message/<ID>`). Email verification is on, so the password is
  set after the link, as on computor.at
  ([computor-org/issues#441](https://github.com/computor-org/issues/issues/441)).
- **Returning learner** `qa-returning@example.com`: enrolled in *Data Science
  mit Python – Grundlagen*, real test results on the first four assignments of
  week 1 (reference solutions on two, an empty file on basis2, the reference
  solution without its docstring on plot_docstr), the next assignment open, and a stopped
  workspace. Without the examples package this step stops with an error.
- **Second learner** `qa-second@example.com`: the same course, math_constants
  solved, an empty file on basis1, and a stopped workspace.
- **Lecturer** `qa-lecturer@example.com` and **admin** `qa-admin@example.com`.
- **Personal tester** (optional): an account for a human tester that no agent
  uses, defined only in `QA_HOME/personal.env` (mode 0600) with
  `QA_PERSONAL_USERNAME`, `QA_PERSONAL_EMAIL` and `QA_PERSONAL_PASSWORD`. Every
  run merges it into the personas, so `reset` recreates it.
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

## Course update rehearsal

This rehearses what a lecturer does on computor.at when the course content
changes, with learners who already have progress. It uses the same web pages
as on computor.at; only the baseline is scripted.

1. Baseline = pinned production backend 74ba88d8, private examples
   9bdb0b271afb and mirror 339bc4a79fc1. Resolve full commits, record deployed
   identities independently, and keep the extension at its production ref.

   ```bash
   # where glab is signed in
   QA_INPUTS=~/qa-inputs ops/qa/fetch_examples.sh main mailuefterl:/mnt/storage/computor-qa-inputs
   # on the QA host
   ops/qa/qactl.sh deploy --backend-ref origin/main --vsix none --content-ref main \
       --examples /mnt/storage/computor-qa-inputs/examples-<main12>.tar.gz
   ```

   This baseline command deletes all existing QA learner state. Run it before
   capturing the before-state, never during the preservation comparison.

   The seed gives the returning and the second learner graded submissions
   and stopped workspaces. Open each learner's workspace once so that their
   repositories exist, and record the state:

   ```bash
   # Export full QA_BACKEND_COMMIT, QA_EXAMPLES_COMMIT, QA_MIRROR_COMMIT.
   set -a; . <(ssh mailuefterl cat /mnt/storage/computor-qa/credentials.env); set +a
   QA_FILES_HOST=mailuefterl QA_PHASE=learners QA_LABEL=before QA_WORKSPACE=1 QA_SCREENS=~/rehearsal \
   QA_PLAYWRIGHT_FROM=/path/with/node_modules node ops/qa/smoke/course-update.mjs
   ```

2. Update to examples ref X and mirror ref Y through the lecturer's pages:

   ```bash
   # Candidate application/image update preserves the captured learner state.
   ops/qa/qactl.sh deploy --backend-ref origin/candidate --vsix /path/to/candidate.vsix
   QA_INPUTS=~/qa-inputs ops/qa/fetch_examples.sh X            # examples-<X12>.zip
   QA_PHASE=update QA_LABEL=update QA_EXAMPLES_ZIP=~/qa-inputs/examples-<X12>.zip \
   QA_SCREENS=~/rehearsal node ops/qa/smoke/course-update.mjs
   ops/qa/qactl.sh reader --content-ref Y                        # on the QA host
   ```

   The script signs in as the admin, uploads the zip on *Examples → Default
   Examples → Upload examples* and opens *Grundlagen → Lecturer → Assignments*,
   where it releases whatever is pending. It prints every message the pages
   show. The mirror's course manifests cannot be re-applied to a running
   course (`deploy-course` refuses an existing path), so structural changes
   have to be made by hand on the lecturer pages.

   Do not add `deploy --content-ref` or `deploy --examples` here: either would
   erase the learners whose state the rehearsal must preserve. Keep the actual
   native manifest changes and example-version provenance with the evidence,
   independently of the baseline import refs printed by `status`.

3. Record what the learners see afterwards:

   ```bash
   # Export full candidate QA_{BACKEND,EXAMPLES,MIRROR}_COMMIT identities.
   QA_FILES_HOST=mailuefterl QA_BEFORE_STATE=~/rehearsal/before-state.json \
   QA_PHASE=learners QA_LABEL=after QA_WORKSPACE=1 QA_SCREENS=~/rehearsal node ops/qa/smoke/course-update.mjs
   ```

   Both learner API tokens (`QA_RETURNING_API_TOKEN`, `QA_SECOND_API_TOKEN`)
   and `QA_ADMIN_API_TOKEN` are required. Mode-0600 snapshots compare exact
   course, result, submission artifact, submission group/repository and workspace
   identities. A changed deployed revision and changed first-assignment text
   are required for both learners. Only the after comparison prints PASS.
   Baseline capture and upload completion alone cannot pass the rehearsal.
   Keep snapshots and screenshots outside repositories.

   Inspect screenshots and open each existing learner repository/workspace.
   The baseline script uses the ordinary workspace terminal to append a harmless
   comment to mathc.py and create an untracked QA sentinel, without replacing
   existing work. Read-only Docker inspection captures their hashes, repository
   HEAD and README hashes. After release it invokes Student Refresh and requires
   changed README/repository revisions with both learner files preserved. Actual
   Test/Submit and the real lecturer control must also pass before acceptance.
   The script uses the native localized lecturer select-latest and publish controls,
   polls the deployed versions, and fails if the controls or changed versions are absent.

   Offline oracle checks: `node --test ops/qa/smoke/course-update-state.test.mjs`.

## Nightly runs

Scheduling belongs in computor-infra. A nightly job needs: a checkout of this
repository on the QA host, `ops/qa/qactl.sh reset` (or `deploy` with the refs
under test), the smoke run above with a Playwright install, and somewhere to
keep the screenshots. It must not run while another job uses port 5000.

The QA overlay runs a dedicated support queue worker from the existing core
worker image. Welcome mail is enabled on the API and worker, SMTP goes only to
Mailpit without STARTTLS or authentication, and mailbox import is disabled.
Verify signup-to-welcome delivery in Mailpit after deploying the matching backend
welcome-mail changes. No external SMTP or IMAP account is involved.
