# 2026.10 — solo backlog (computor-fullstack + computor-vsc-extension)

Scope: issues a senior developer can land alone in these two repos. Course
content, example authoring, didactics, Netidee paperwork, the `computor-agent`
tutor and multi-party ops decisions are out.

Every item was checked against the code on 2026-08-26. Where the check showed
the work is already there, the item says so instead of pretending it is open.

Companion file: `ISSUES-2026.10-STATUS.md` — ten issues already fixed and
closable without code.

Checked against `b81048ec` (fullstack) and `cde5560` (extension). Neither of
those two commits closes a backlog item — #375 and #362 are outside this
scope — but #375 is cross-referenced under #350 and #351, whose UI work lands
on the surface it changed.

**Legend**

| Tag | Meaning |
|---|---|
| **OPEN** | verified still broken / missing, steps below |
| **ALREADY DONE** | verified implemented; close after a re-test |
| **PARTLY DONE** | half exists; the remaining half is scoped below |
| **NEEDS DECISION** | the code deliberately does the opposite; you must choose |

---

# Part 1 — Sandbox and grading integrity (P0)

The release-blocking bucket. Do it first and in this order — #239 is a
prerequisite for the #240 attack, and #240/#241 share one mechanism.

`computor-testing/sandbox/` is **not** an isolation boundary. It is a static
analyser (`sandbox/security.py`) plus a resource-limited subprocess wrapper.
The production path never goes through `Dockerfile.sandbox`. Its header already
documents the right recipe (`--network none --read-only --cap-drop ALL
--pids-limit`); nothing runs it.

## #239 — reference and spec paths disclosed in `result_json`  — **OPEN**

**Verified root cause.** Two sites write absolute container paths into the
report the student reads back:

- `computor-testing/testers/tests/conftest_base.py:448-453`
- `computor-testing/testers/tests/octave/conftest.py:376-381`

```python
report.properties = {
    "test": testyamlfile,          # /tmp/examples/by-version/<key>/<id>/test.yaml
    "specification": specyamlfile, # /tmp/tmpXXXX.yaml — contains referenceSolution
    "pytestflags": pytestflags,
    "exitcode": str(exitstatus),
}
```

Note the cache path changed with the #309 fix — it is now
`/tmp/examples/by-version/{version_key}/{identifier}/` — but it is still
disclosed verbatim, so the disclosure is unchanged in kind.

**Steps**

1. In both conftests, stop putting filesystem paths in `report.properties`.
   Keep `pytestflags` and `exitcode`. If the basename is genuinely useful for
   debugging, emit `os.path.basename(...)`, never the directory.
2. Log the full paths through `logger.info` instead, so worker logs keep them.
3. Add a defensive strip in the backend where the report is read
   (`tasks/temporal_student_testing.py:518-521`): drop any `properties` key
   whose value looks like an absolute path. This covers other testers and any
   future one that forgets.
4. Historic results already in the DB carry the paths. Decide: one-off UPDATE
   over `result.result_json`, or filter on read. Prefer the UPDATE — a read
   filter is easy to bypass through an export route.
5. Add a regression test asserting no value in `properties` starts with `/`.

**Done when** a student-visible result for a Python and an Octave assignment
contains no absolute path, and older results have been scrubbed.

## #240 — reference solution readable by the student subprocess — **OPEN**

**Verified root cause.** `tasks/temporal_student_testing.py:440-500`: the
activity resolves `reference_path` (the cached example directory, master
solution included) and `student_path` on the same filesystem, then runs the
tester as an ordinary subprocess of the worker — same UID (`worker`), same
`/tmp`, no namespace. `job_config` even carries `reference_path` explicitly.

**Steps**

1. Decide the isolation mechanism — this is the one design call in Part 1, and
   it also settles #241. Recommendation: **bubblewrap/`unshare` inside the
   existing worker container**, not a nested Docker run (the worker is
   deliberately non-root and has no docker socket; giving it one would be a
   larger hole than the one being closed).
2. Write one launcher — `computor-testing/sandbox/launch.py` — that runs a
   command with: a fresh mount namespace, `--ro-bind` only the student
   directory and the specific test files the run needs, a `tmpfs` `/tmp`, and
   an unshared network namespace (that is #241).
3. The reference directory must not be in the bind set at all. Where the tester
   genuinely needs reference *values*, compute them **outside** the sandbox and
   pass the values in — not the files. This is the small first step toward
   #238.
4. Belt and braces for anything still on the shared filesystem: create the
   version cache `0700` under a dedicated UID the student process does not run
   as. Note that `no-new-privileges:true` is set on the service, so a setuid
   helper will not work — use user namespaces.
5. Verify by submitting the exact probe from the issue: `os.listdir` of the
   old reference path plus an open of `*_master.py`. Both must fail.

**Done when** a submission that tries to read the reference gets `ENOENT` or
`EACCES`, and a normal submission still grades identically.

## #241 — student subprocess has full network access — **OPEN**

**Verified root cause.** `ops/docker/docker-compose.prod.yaml:243-283` — the
`temporal-worker-testing` service sits on `computor-network` with the default
bridge egress, alongside `postgres`, `redis` and `minio` (it `depends_on` all
three). Anything it spawns inherits that reachability.

**Steps**

1. Do the network half of the #240 launcher: unshare the net namespace for the
   student process. The worker keeps its own connections; the child gets a
   loopback-only stack. This is the actual fix — everything below is depth.
2. Second layer, compose-side: give the testing workers their own network with
   no route to `postgres`/`minio`, and reach the API through Traefik rather
   than the shared bridge. Keep Temporal reachable — the worker needs it.
3. Third layer, egress: block outbound to the public internet from the testing
   network unless a language runtime genuinely needs it (`PYTHON_TEST_
   REQUIREMENTS` installs at build time, not run time — confirm before
   blocking).
4. Re-run the issue's probe table (redis 6379, postgres 5437, minio 9000,
   8.8.8.8:53, 1.1.1.1:443). All must be refused.

### Sub-finding while checking #241 — worth its own line

`computor-backend/src/computor_backend/testing/backends.py:258` launches the
tester with `subprocess.run(cmd, shell=True, ...)` and **no `env=`**, so the
tester process inherits the whole worker environment, `API_TOKEN`
(= `TESTING_WORKER_TOKEN`) included.

Student code is not directly exposed today, because the language executors
build a clean allowlist environment for the child
(`ctexec/base.py:171-179` → `get_safe_env`, used by `python.py:65`, `r.py:51`,
`octave.py:60`, `julia.py:83`). Two gaps remain:

- `testers/executors/document.py:114` passes `use_safe_env=False`, which falls
  back to `filter_env(os.environ)` — an **exact-name** blocklist
  (`ctexec/environment.py:13-68`) that does **not** contain `API_TOKEN`.
- Nothing stops a future executor from repeating that.

**Steps:** add `API_TOKEN`, `TESTING_WORKER_TOKEN` and `COMPUTOR_*` to
`BLOCKED_ENV_VARS`; pass an explicit `env=` at `backends.py:258`; drop
`shell=True` and pass the argv list (the parts are already built at
`backends.py:240-247`).

## #232 — skipped tests reduce the grade — **OPEN**

**Verified root cause.** Unchanged from the issue text, at a new line number:

- `computor-testing/testers/tests/test_base.py:820` —
  `pytest.skip(f"Variable \`{name}\` not found in reference namespace")`
- `testers/tests/conftest_base.py:949-958` — `skipped` is summed and reported,
  but `total` still includes it
- `computor-backend/.../tasks/temporal_student_testing.py:533` —
  `result_value = p / max(t, 1)`, and `extract_test_counts`
  (`tasks/temporal_base.py:159-168`) never looks at `skipped`

So every skip is a silent point off.

**Steps**

1. Separate the two kinds of skip. A missing variable **in the reference** is a
   lecturer authoring error, not a student outcome — make line 820 fail loudly
   with a message naming the example and variable, so it surfaces during
   authoring instead of quietly taxing students.
2. For legitimate skips (`Unsupported qualification`, `Structural/Error/
   Warning/Linting tests not implemented for this language`,
   `test_base.py:1196-1208`), exclude them from the denominator: teach
   `extract_test_counts` to return `skipped` and compute
   `result_value = passed / max(total - skipped, 1)`.
3. Guard the degenerate case: `total == skipped` must not become 100%. Report
   it as an inconclusive run, not a pass.
4. Backfill decision: results graded under the old formula are wrong. Either
   recompute `result_value` from the stored `result_json`, or accept and
   document it. Recomputation is straightforward — the counts are in the blob.
5. Regression test: one sub-test skipped out of four correct → grade 1.0, not
   0.75.

## #237 — the security gate (umbrella) — **OPEN, tracking only**

Close #239, #240 and #241 plus the env-hygiene sub-finding, then re-read the
rest of the issue and either close each remaining bullet or record an explicit,
named risk acceptance. Do not close #237 silently on the back of the three
children.

## #238 — artifact-based grading epic — **OPEN, design only this cycle**

Do not start the implementation before the release. Two things are worth doing
now because they cost little and shrink the epic later:

1. Write the golden-record format down (what a recorded reference run contains,
   how it is versioned against an example version, how it is invalidated).
2. Build step 3 of #240 — computing reference values outside the sandbox — in a
   way that could later read a recorded artifact instead of executing the
   reference live. That is the seam the whole epic turns on.

---

# Part 2 — Testing pipeline correctness (P1)

Most of this bucket turned out to be done already. What is left is small.

## #234 — Python testing with NaN — **ALREADY DONE**

Both halves of the issue are implemented.

*NaN equality* is now unconditional, not opt-in:

- `computor-testing/testers/tests/test_base.py:368` —
  `np.allclose(..., equal_nan=True)` for numeric arrays
- `test_base.py:385-394` — explicit scalar NaN path, `NaN == NaN` returns equal
- `ctcore/helpers.py:168,182-188` — same in the helper comparator

Landed as `feature/testing-is-nan` (PR #97, `9453b81d`), later extended by
`58ba6dcc` (richer assertion messages).

*Error tests in Python* exist too: `testers/tests/python/test_class.py:583`
calls `check_error(sol_student, sub.pattern)`, implemented at
`test_base.py:727-738`. The claim "MATLAB can test error messages but Python
cannot" is no longer true.

**Steps to close**

1. Re-run `sindex` (Week 2), `quadratic_eq(_for)` and `quadratic_eq_eval`
   (Week 6) without the `np.where(np.isnan(x1_raw), -999.0, x1_raw)`
   workaround. They should pass on NaN directly.
2. Remove the workaround from those three examples once confirmed.
3. One real leftover: **`equalNaN: true` in `test.yaml` is not a recognised
   key** — nothing reads it, it is silently ignored, which is exactly why it
   "didn't fix it". Decide whether to accept-and-ignore it or reject it in
   schema validation. Silent ignore is what burned the reporter; reject it.

## #121 — "Course content not found" after Submit then Test — **OPEN, needs repro first**

Could not be pinned statically. The string comes from ten places; the plausible
one on this path is `api/submissions.py:247` (artifact listing filtered by
`course_content_id`).

Two extension fixes since the report may already cover it —
`fix/271-submit-auto-test` (`b03690f6`) and `fix/2026.10-submit-tested-commit`
(`bd0862c`, "never submit an older or untested commit behind the student's
back").

**Steps**

1. Reproduce on the current build: Python course, Submit, then Test
   immediately. If it no longer reproduces, close it and say which fix covered
   it.
2. If it does: log the `course_content_id` the extension sends on the Test call
   and compare it with the one it held before Submit. The likely shape is the
   tree being rebuilt by the post-submit refresh while the command still holds
   the old item.
3. Fix by resolving the content id at invocation time from the course id +
   path, rather than capturing the tree item.

## #343 — MATLAB testing framework into the repo — **WON'T DO**

Decision (Max, 2026-08-26): the framework will not be migrated into the
monorepo. A MATLAB lecturer clones
`git@gitlab.tugraz.at:codeability/testing-frameworks/computer-matlab-testing.git`
into their workspace by hand and works with it there.

**Steps to close:** comment that on the issue (plain voice) and close it.
No code.

---

# Part 3 — Deployment and content lifecycle (P1/P2)

Two confirmed root causes here, both small fixes with real user impact.

## #336 — assignment update never reaches students — **OPEN, highest value in this part**

The write path itself is sound: assigning a new version resets the deployment
to `pending` (`business_logic/lecturer_deployment.py:375`), and a release picks
up `pending` and `failed`
(`tasks/student_template/selection.py:36-47`), downloads from MinIO and writes
the directory (`tasks/temporal_student_template_v2.py:414-460`).

So the failure is upstream of the release. **Correction after a deeper trace**
(see the dedicated plan at the end of this file): the extension's release flow
is more correct than first assumed — update candidates DO get
`upgrade-versions` (re-assign to latest, reset to pending) before the
template release runs with an explicit content selection. The remaining
suspects are: the update never being *offered* (`has_newer_version` computed
false), the new version's files missing under its MinIO `storage_path`, or a
pure display bug. The dedicated plan carries the four-branch diagnosis tree;
follow that, not the paragraph that used to stand here.

**Steps**

1. Reproduce with the DB in view: after upload + deploy, read
   `course_content_deployment` for that content — `example_version_id`,
   `version_tag`, `deployment_status`. That single row decides which of the two
   stories is true.
2. If the row still says 1.0.1: the bug is that "upload a new version" does not
   re-assign. Make the lecturer's deploy action call assign-with-the-new-version
   before releasing, or offer an explicit "update to latest version" action.
   `validate_reassignment_allowed`
   (`lecturer_deployment.py:57-80`) already permits a version bump on the same
   example, so no permission work is needed.
3. If the row says 1.0.3 but the repo still has 1.0.1: the bug is in the release
   run — check whether `download_example_files` resolved the new
   `example_version` or a stale relation, and whether the run reported errors it
   swallowed.
4. Either way, fix the display: show the **deployed** version in the tree hover
   and in Details, and show the available version separately. The current
   conflation is what made this take weeks to notice.
5. Clear the misleading banner the reporter saw — "Cannot unassign while the
   status is deployed" is being shown on a screen where unassign is not what
   the user is trying to do.

**Done when** upload → deploy moves the student template to the new version, or
tells the lecturer exactly what is still required, and the version shown is the
version deployed.

## #150 — duplicate example in two units — **OPEN, root cause confirmed**

**Verified root cause.** The student-template directory name comes from the
example identifier, not the course content:
`tasks/student_template/selection.py:50-84` —
`deployment_path` → `example_identifier` → `example.identifier`. There is **no**
uniqueness guard anywhere in `temporal_student_template_v2.py` or
`student_template/`. Two course contents in different units using the same
example resolve to the *same* directory, the second write overwrites the first,
and the student's second assignment resolves onto the first one's directory —
which is the duplicate error in the report.

**Steps**

1. Make `deployment_path` unique per course at assign time. When the resolved
   name is already taken by another deployment in the same course, append a
   discriminator derived from the course-content path (the unit segment reads
   best: `mathematical_constants-week2`).
2. Enforce it: a unique constraint on `(course_id, deployment_path)`, with a
   migration. Without the constraint this will regress.
3. Do **not** retro-rename existing directories — that would move files under
   students who have already cloned. Only new/changed deployments get the
   discriminator.
4. Add the reverse guard on the student side: opening an assignment must
   resolve through the deployment record, not by scanning for a directory whose
   name matches the example.
5. Regression test: same example assigned to two units in one course, both
   deploy, both open.

## #162 — created content does not appear until a hard reload — **OPEN, root cause confirmed**

**Verified root cause.** `computor-vsc-extension/src/ui/tree/lecturer/
LecturerTreeDataProvider.ts:1150-1165`:

```ts
const created = await this.apiService.createCourseContent(...);

// Clear cache and refresh
// Cache cleared via API          <- comment lies; there is no call

if (parentPath) {
  const parentContent = existingContents.find(c => c.path === parentPath);
  if (parentContent) {
    this.refreshNode();           // only when the parent happens to be found
  }
} else {
  this.refreshNode(folderItem);
}
```

The course cache is never cleared, and the refresh is conditional on finding
the parent in a list that was read *before* the create. `createAssignment`
(`LecturerCommands.ts:1234`) hides this by calling `forceRefreshCourse`
afterwards. `createUnit` (`LecturerCommands.ts:1128`) does not — which is
exactly the reported flow, "select a type (mandatory, and the custom type
Lecture below)", i.e. a unit.

**Steps**

1. In `createCourseContent`, call `this.apiService.clearCourseCache(
   folderItem.course.id)` and refresh unconditionally. Delete the two lying
   comments.
2. Have `createUnit` await and use the return value the same way
   `createAssignment` does, so a failed create is visible.
3. Check the same pattern in `updateCourseContent` (line 1172) and
   `deleteCourseContent` — `updateCourseContent` does clear the cache, so the
   inconsistency is only in create.
4. Verify with the reporter's exact flow, including a custom content type.

## #163 — undeployed content visible in the student view — **OPEN**

**Verified root cause.** `repositories/student_view.py:107-119` filters student
content on **visibility** (`is_content_visible`, from the #338 work) but never
on deployment state. An assignment that has been created but not deployed is
still listed, which is what the reporter saw — name and type, no files.

**Steps**

1. In the student list and get paths, hide submittable content whose
   deployment is missing or whose `deployment_status` is not `deployed`.
2. Leave units alone — they have no deployment. A unit whose children are all
   hidden should collapse to nothing; confirm the tree does that rather than
   showing an empty unit.
3. Reuse the #338 veto rather than adding a second filtering mechanism —
   `visible_effective` already carries "student may not see this" through the
   response. Fold "not deployed" into the same computation so there is one
   answer, not two.
4. Staff keep seeing everything, exactly as with #338.
5. Regression test: create an assignment, do not deploy, switch to student
   view — nothing appears; deploy — it appears.

## #146 — rearranging assignments — **ALREADY DONE**

Both halves the issue asks for exist.

Backend: `POST /course-contents/{content_id}/move`
(`api/course_contents.py:551-623`) takes a path and a position, validates and
applies the move with an ltree cascade
(`business_logic/course_content_move.py`), and broadcasts `reordered`.
`CourseContent.position` is a float column (`model/course.py:250`), so
insertion between siblings needs no renumbering.

Extension commands (`package.json`):

- `computor.lecturer.moveContentToTop` / `moveContentUp` / `moveContentDown` /
  `moveContentToBottom` — change the order
- `computor.lecturer.prependContentToUnit` / `appendContentToUnit`
  ("Move to Start/End of Unit…") — move between units

Landed as `feat/323-content-move-hardening` + `feat/323-content-reordering`.

**Steps to close:** have Winfried do both operations once on the current build;
if they behave, close referencing #323.

## #147 — set deployed assignments invisible — **ALREADY DONE (see #338)**

Superseded by #338, which shipped in both repos. Close as a duplicate.

---

# Part 4 — Identity, tokens, sessions (P0/P1)

## #178 — Keycloak SSO: finish and enable for production — **ALREADY DONE**

The issue text ("never been used in production") is out of date. Keycloak runs
in production: `ops/docker/docker-compose.keycloak-prod.yaml` defines the
service, `docker-compose.prod.yaml` carries the backend-side wiring including
the Forgejo OIDC client reconciliation on startup, and the extension moved to
SSO login (`refactor/sso-login`, `feat/unified-login-approach`). GitLab login
was removed outright (`refactor/remove-gitlab-login`).

The clinching evidence is issue **#333** itself, filed on 2026-08: a student
writes "I do not have a password because now I always used keycloak to login."
Students are logging in through Keycloak on `code.tugraz.at` today.

**Steps to close:** re-read the issue's Done/Missing checklist against the
current code, tick what shipped, and either close it or split whatever single
bullet is genuinely outstanding into its own issue. Do not leave a P0 open
because its description is stale.

## #333 + #342 — Forgejo clone URL and token — **PARTLY DONE, small remainder**

Backend is done (see `ISSUES-2026.10-STATUS.md`):
`POST /user/courses/{course_id}/provision-repository` mints and returns
`clone_token` + `clone_username` (`api/user.py:180-210`), minted once per user
per instance, with `rotate=true` as the escape hatch. The extension consumes it
(`StudentRepositoryManager.ts:644-662`) and clones fine.

Missing: a student has no way to *see* a working credential, so copying the
clone URL out of the Forgejo web UI leads to a password prompt for an account
that only ever had Keycloak.

**Steps**

1. Add a student command — "Copy git clone command" — that returns the ready
   line: `git clone https://<clone_username>:<clone_token>@<host>/<owner>/<repo>.git`.
   The value already exists on the client; this is a clipboard write plus a
   warning that the line contains a credential.
2. Same on the web course page, next to the repository link.
3. Say what the credential is where the student looks for it: a short note in
   the student help that Forgejo has no password under SSO, and that this token
   is the terminal credential.
4. Handle the null case: `clone_token` is null until the student has logged
   into Forgejo once. Trigger the provisioning call rather than showing an
   empty box.
5. Close #342 as a duplicate of #333.

## #257 — WebSocket disconnects leave clients in stale auth state — **DONE** (2026-08-26)

**Verified root cause.** `websocket/auth.py` authenticated once at handshake
(`4001 Invalid or expired token` at lines 92 and 119) and never re-validated.
There was no expiry watch on an established connection. Only the SSO session key
was refreshed (`auth.py:145`). So when the token behind a live socket expired,
HTTP started returning 401 while the socket sat there, which is exactly the
production trace in the report.

Landed on `fix/257-ws-token-expiry` in **both** repos — see Part 4's entry for
what each step became. Steps 1, 2, 4 and 5 held as written; step 3 needed
correcting on the web half and the plan's optional step 2 turned out to be
worth doing.

**Steps**

1. ~~Record the token's expiry at handshake and close the socket with a
   distinct application close code when it passes.~~ Done — `4003`, watched by
   a task running beside the receive loop. The deadline is re-read on every
   wake rather than captured, because SSO TTLs slide.
2. ~~On the client, treat that close code as "refresh the session".~~ Done —
   silent refresh, reconnect, and only then hand over to #247's
   `CredentialRecoveryService`.
3. **Extension only.** `computor-web` has no WebSocket client — only the
   generated event types — so there was nothing there to redirect. Nothing to
   do until one exists.
4. ~~Do not reuse a token already known to be dead.~~ Done — the rejected token
   is remembered and refused, which is what stopped the retry loop.
5. ~~Reproduce by minting a short-lived token.~~ Done, both credential kinds:
   a 20s API token closed 4003 at t+19.7s, and an SSO session deleted
   mid-connection closed 4003 at the next re-check.

**Beyond the plan:** `system:auth_expiring` + `system:reauth` let a client
re-arm a live connection instead of dropping every subscription and rebuilding
it a moment later. The plan marked this optional; it is what makes an hourly
session boundary invisible rather than merely survivable.

## #247 — token expiry error flow polish — **DONE** (2026-08-26)

Landed on the extension's `release/2026.10` as `a4e8a77` (branch
`fix/247-token-expiry-ux`, five commits).

All three acceptance boxes are ticked, and the plan's steps 1–4 held up — this
one needed no correction.

`src/services/CredentialRecoveryService.ts` is the new single answer to "a
credential just died — now what?", and every 401 surface routes through it:

1. **Identity.** A rejected credential now names itself. The backend case says
   the *sign-in* expired and offers `Sign in` / `Use API Token`; the git case
   names the server whose token was rejected. Neither says "unreachable" — that
   word stays with `BackendConnectionService.showConnectionError()`, which is
   what #117 settled. A unit test pins the two apart.
   `AuthenticationErrorStrategy` used to say "Authentication failed … please
   reload the window", which was both the wrong fix and — because it *awaited*
   its own dialog — the blocking prompt `probeToken`'s comment warns about. It
   no longer blocks.
2. **Destination.** `computor.settingsView` takes an optional
   `{ section, url }`. The provider passes it into the webview's initial state,
   and `applyFocus()` in `settings-view.js` expands that server's *Update*
   panel (or opens a pre-filled new entry when nothing is stored yet), scrolls
   it into view, focuses the token input and flashes it. Re-showing an
   already-open panel re-renders it, so the deep link works either way. The
   focus is consumed once — a later validation result must not yank focus back.
3. **Continuity.** `commandRegistrar` is the one place that knows both the
   command id and its arguments, so its existing safety net now asks the
   service first: a credential failure is remembered as
   `{command, args, label}` and reported; anything else falls through to
   `showErrorWithSeverity` unchanged. On `credentialRestored(realm)` a read
   (the eight `*.refresh` commands) replays silently and anything else gets a
   `Retry "<action>"?` button. Writes are never auto-run.

Two details worth keeping:

- The git realm is identified by parsing the URL git quoted back
  (`extractAuthFailureOrigin` in `utils/gitErrors.ts`). `URL.origin` drops
  userinfo, so a remote carrying its token inline — which is how this extension
  writes them — can never leak that token into a notification or a webview. A
  test pins it.
- `RepositoryTokenManager.storeToken()` fires the retry only *after*
  `updateWorkspaceRemotes()` settles. A retry that beat the remote rewrite
  would re-authenticate with the token that just died.

**Deliberately not done:** managed-Forgejo push failures keep their existing
`Fix Authentication` route (`escalatePushFailure`). Students never see that
backend-minted token, so a Settings deep link there is the dead end #318
already removed once.

**Verify:** `npm run test:unit` — 1053 passing. Manual pass: corrupt a stored
provider token, trigger a clone/push, confirm the notification names the server
and its button lands on that server's token field, then save a good token and
take the offered retry.

**#248 (self-rotation) picks this up unchanged** — it should call
`reportExpired`/`credentialRestored` rather than inventing a second path, which
is what step 4 asked for.

## #248 — token self-rotation — **OPEN, P3, record only**

Out of scope for this release, by the issue's own text. When picked up: detect
expiry within N days at startup, mint a successor with the existing credential,
swap it in, notify non-blockingly. #247's plumbing now exists and is what to
build on: `CredentialRecoveryService.reportExpired` /`credentialRestored` in
the extension, keyed by realm.

## #244 — API-only test-user lifecycle — **PARTLY DONE, needs re-scoping**

Three of the report's five dead ends have moved since it was written:

- **Bug #1 is gone.** `api/team_management.py` no longer exists — the module was
  removed with `refactor/remove-team-formation` (only stale `.pyc` files
  remain). The `my-team` 500 (`'UUID' object has no attribute 'replace'`) is
  not reachable.
- **User deletion works.** `DELETE /users/{id}` cascade was fixed
  (`fix/user-delete-profile-cascade`), so orphans are no longer permanent.
- **An invite flow now exists** — `api/invites.py`: create, list, get, revoke,
  public get, accept. This covers part of what the issue asked for.

Still true:

- `POST /api-tokens/admin/create` is admin or `_service_manager` only
  (`api/api_tokens.py:44-62`) — a lecturer still cannot mint a token for a
  student on their own course.
- `course_group_id` is required by the DB for `_student` course members but not
  declared in the OpenAPI schema.
- `predefined_token` accepts `minLength: 32` but auth requires exactly
  `ctp_` + 32 chars, so a longer value is accepted at create and fails on every
  later request.
- Bug #2 (`SubmissionGroupCreate` schema/DB mismatch on `course_id`) — verify
  against the current submission-group provisioning service before assuming it
  survived the refactor.

**Steps**

1. Re-run the walkthrough on the current build and rewrite the issue to what
   still fails. Half of it is stale.
2. Fix the two cheap schema-truth bugs regardless: declare `course_group_id`
   required for students, and make `predefined_token` validation agree between
   create and use.
3. For the actual goal — bootstrapping synthetic students — point at
   `seed.sh`, which already creates fake users and enrolments directly against
   the DB with a `--cleanup` flag. That is the supported answer today and it
   should be documented in the issue rather than reinvented over HTTP.
4. Only then decide whether lecturers get token-minting for their own students.
   That is a real permission widening and deserves its own decision, not a
   drive-by.

## #262 — per-course grader access via Keycloak — **DONE** (`test/262-grading-access`, 2026-08-26)

The grant was already implemented. Step 1 below asked to reuse the course-role
machinery "if a course role can express it" — it can, and the role already
exists: **a grader is a `_tutor` on that one course**. Enrolling the person
there lets them grade there and nowhere else, which is the whole of what the
issue asks. No new role, no parallel table, no new Keycloak claim — identity
comes from Keycloak, the grant lives in the database.

Steps 2 and 3 were already satisfied too. Enforcement is structural rather
than per-endpoint: `CoursePermissionQueryBuilder.filter_by_course_membership`
(`permissions/query_builders.py:54-56`) constrains every membership lookup to
the courses where the caller holds the required role, so the endpoint and the
route gating cannot disagree — they read the same memberships. Route hiding
falls out of `/user/views/{course_id}` answering `["student","tutor"]` for a
`_tutor` (`business_logic/users.py:16-19`) while the web's grading pages sit
under the Lecturer section (`Sidebar.tsx:131-135`).

Only step 4 was missing, and it is now `tests/test_grading_access.py` (16
tests, all passing).

**The one thing worth writing down**, because it is the question the issue
invites and the answer is not obvious from the file names: the two grading
surfaces sit at different floors *on purpose*.

- `_tutor` grades a student's submitted work — `create_artifact_grade`
  (`business_logic/submissions.py:701`), `check_artifact_access` (`:578-604`).
- `_lecturer` gets `course_member_gradings`
  (`repositories/course_member_gradings_view.py:200,266,375`), the course-wide
  progress matrix over every member. That is a course-management statistic,
  not an act of grading.

Neither floor moved, and neither should: lowering the matrix to `_tutor` would
hand every tutor in every course a report they are not meant to have, and a
`_grader` role inserted below `_lecturer` would differ from `_tutor` by exactly
that one report.

## #185 — email for notifications and sign-up — **OPEN, unstarted**

Verified: there is no SMTP, mail or notification-sending module anywhere in the
backend. The account was obtained (first checkbox ticked); nothing is wired.

**Steps**

1. Pick the transport and put its credentials in `.env` with the
   `${VAR:?must be set}` form — no defaults.
2. One small sending service with a template per event. Do not scatter
   `smtplib` calls through business logic.
3. Send asynchronously through the existing Temporal worker, so a slow or dead
   relay never blocks a request.
4. Start with exactly two events — sign-up verification and invite — because
   those are what #176 and the invite flow need. Resist the "notifications"
   list in the issue until those two work.
5. Dev must not send real mail: a console/file transport by default, real SMTP
   only when configured.

## #176 / #179 / #236 — sign-up refactor, GitLab token strategy, multi-provider — **OPEN, not solo-sprint items**

These are multi-week arcs, listed for completeness.

- **#179 is a decision, not code.** Nothing else should start until you choose
  between keeping tokens in the OS keyring, a self-hosted token service, or
  something else. Write the decision into the issue and close it.
- **#176** depends on #185 (verification email) and on #179's outcome. The
  webview part is already done on `feature/sign-up-webview`.
- **#236** is worth doing only once a second provider is actually required.
  Today Keycloak brokers the external IdPs, which covers the real need.

---

# Part 5 — Capacity and operability (P0/P1/P2)

## #351 — limit concurrent users — **DONE** (`feat/351-capacity-limits`, 2026-08-26)

The entry below said "partly done". It was wrong: **neither** of #351's limits
existed. `enforce_template_quota` is a third, different limit —

> The cap counts running/starting workspaces of the template across ALL users
> and applies to everyone, admins included — it models hard capacity (e.g.
> MATLAB license seats), which exceeding would break anyway.

— and step 1 below (leave it alone) was the only step already satisfied. All
three limits now exist side by side. What landed:

1. `instance_settings`, a singleton table holding `max_workspace_users`,
   `max_concurrent_logins` and `login_idle_minutes` (`null` = unlimited),
   editable at runtime from `/admin/limits` via `GET/PUT /system/limits` —
   step 5 taken in its DB-backed form, not the env-only fallback.
2. The workspace limit caps **distinct users**, not workspaces: the issue asks
   for "maximum number of workspace users", so a user with two workspaces
   spends one seat and is never refused their second. Enforced at provision,
   start and lecturer bulk-provision through `enforce_workspace_admission`,
   which shares one Coder fleet listing with the template quota rather than
   fetching it twice.
3. The login limit caps distinct signed-in users, seats held in a Redis sorted
   set keyed by user id (two tabs = one seat), taken at the SSO callback,
   refreshed on each Principal-cache miss and released on logout.
4. Both refusals name the limit, the current number and the local VS Code
   alternative, linked when `EXTENSION_PUBLIC_DOWNLOAD_URL` is set. A cap of
   `0` reads as "switched off" rather than "full".
5. Staff bypass is an explicit role list, not the `_` prefix — see the
   corrected plan in Part 8 for why that distinction is load-bearing.

Step 6 (feed #350's numbers in) stays open by design: the issue asks for a hard
limit *"in the meantime"*, before the computed one. #350 was therefore **not** a
prerequisite, and #351 shipped without it.

## #350 — missing runtime info on the webpage — **OPEN, cheap and useful**

`GET /instance-info` exists (`api/instance.py:54`) but carries discovery data
(issue-reporting config, URLs), not runtime state.

**Steps**

1. Add a separate `GET /instance-status` — deliberately not folded into
   `instance-info`, which is consent-exempt and public.
2. Return: process start time, build/commit identity, system memory total and
   free, memory attributed to workspaces, and free capacity for workspaces.
3. Nothing sensitive: no hostnames, no versions of internal services, no
   credentials. The issue's list is fine as written; keep it to that.
4. Decide who may read it. Recommendation: any authenticated user sees
   capacity (they need it to understand a refusal from #351); admins see the
   rest.
5. Render it on an admin/system page in the web UI, and surface just the
   capacity line wherever a workspace launch can be refused — the course
   workspace rows already poll workspace state since `b81048ec` (#375), so the
   polling loop is there to hang it on.
6. This is the data #368 will measure against, so ship it before #368.

## #366 — local-first VS Code workflow — **OPEN, take one slice**

The full issue is a release-scale arc (onboarding from two entry points, local
running, capacity guard, migration between remote and local, telemetry limits).
Do not take it whole.

**Steps**

1. Take the capacity-guard slice only — it is #351, above, and it is the part
   that blocks the workshop.
2. Second slice, if time allows: "run the official tests without starting a
   Coder workspace". Check first whether the extension's existing test path
   already does this for a locally cloned repo; if it does, the deliverable is
   documentation, not code.
3. Leave onboarding, migration and telemetry to a scoped follow-up issue with
   its own acceptance criteria. Write that follow-up now so the scope split is
   on record.

## #368 — measure Hetzner and workspace capacity — **OPEN, measurement not implementation**

**Steps**

1. Inventory the servers, types, volumes, addresses, firewall and services as
   they actually are, from the Hetzner API and the running hosts.
2. Measure baseline and peak for a representative course: CPU, RAM, disk,
   network, Postgres, Redis, Temporal, Coder, and the Python and MATLAB
   workers separately — MATLAB dominates and averaging it in hides the number.
3. Derive per-workspace and per-test-job budgets, then a headroom rule and an
   admission formula.
4. Publish a dated report with assumptions stated, a recommended next Hetzner
   size, an alert threshold and a cost estimate. No credentials.
5. Wire the formula into #351's guard and the numbers into #350's endpoint.
6. Add a repeatable load test so the number can be re-measured rather than
   re-argued.

---

# Part 6 — Release engineering (P0)

## #85 — release process for the VSIX — **OPEN**

**Verified state.** `computor-vsc-extension/.github/workflows/ci.yml` runs
type-check, lint, unit tests, build and the webview asset check. There is
**no** packaging or publishing step, and the `push` trigger does not include
`release/**` — only `main` and feature-branch globs, so the release branch is
never built on push.

**Steps**

1. Add `release/**` to the CI push trigger. Today the branch you actually ship
   from is only built on pull requests.
2. Add a tag-triggered release job: `vsce package`, attach the VSIX to a GitHub
   release, then `vsce publish` gated on the tag.
3. Store the Marketplace PAT as a repository secret, and record who owns it —
   #363 asks for the publisher to be named.
4. **#115 is a hard blocker here**, not a cosmetic issue: `package.json` has no
   `icon` field, and the Marketplace requires one. Do #115 first.
5. Pin the toolchain (`vsce` version, Node 20 already pinned) so a rebuild from
   a tag produces the same VSIX.
6. Verify the loop end to end on a pre-release tag before the real one.

## #114 + #153 — release model and hotfixes — **OPEN, one decision, then wiring**

Treat as a single piece of work: #153 ("how to hotfix") is unanswerable until
#114's branch model is written down.

**Verified state.** `computor-fullstack/.github/` contains only
`dependabot.yml` — there is **no CI at all** in the backend repo. That is a
direct gap for #363's "reproducible CI evidence".

**Steps**

1. Write the model down in one place: unstable = feature branches, testing =
   `main`, stable = `release/**`, hotfixes cherry-picked, one release per
   semester with a feature freeze date. The issue already contains the
   proposal; it needs a decision, not more discussion.
2. Reconcile it with what the team does now — today all work targets
   `release/2026.10` and `main` is stale. Either the model changes or the
   practice does; do not ship a written model nobody follows.
3. Add CI to `computor-fullstack`: lint, backend test suite, and an image build.
   Baseline with the stack up is 12 failed / 1602 passed, all 12 being 401s
   against a live API in `test_api_endpoints.py` — either fix or explicitly
   exclude those before CI can be a gate.
4. Write the hotfix runbook as a script or a documented `gh` sequence, not
   prose: branch from the release tag, fix, cherry-pick forward, tag, deploy.
5. Close #153 by pointing at the runbook.

## #364 — disposable feature-branch deployments — **OPEN, heavy but solo-doable**

Genuinely useful for the workshop and it lives entirely in `ops/`.

**Steps**

1. Parameterise the compose stack on an environment id: distinct project name,
   network, volumes, ports, and a generated secret set. The `name: computor`
   pin in `docker-compose.base.yaml:12` is what currently forces one stack per
   host — that is the first thing to make variable.
2. One command that takes a repo/branch or PR plus an id, builds, migrates and
   starts the stack, and prints the URL and the commit/image digests.
3. TTL and an explicit destroy that removes only that environment's resources.
   Prove it cannot touch green or blue — the wipe scripts already have this
   discipline for the Coder database; copy it.
4. Never copy production credentials or student data. Seed with `seed.sh`.
5. A quota so several environments can coexist without exhausting the host, and
   a refusal for untrusted branches.
6. Smoke test in the same command: login, course, submission, test run.

---

# Part 7 — VS Code extension papercuts (P2/P3)

Small, independent, good filler between the P0 blocks. Three of them turned out
to be done already, and two need a decision rather than code.

## #115 — add the COMPUTOR logo — **OPEN, and it blocks #85**

**Verified:** `package.json` has no `icon` field. The Marketplace requires one,
so this is a release blocker wearing a P2 label.

**Steps:** add a 128×128 PNG under `resources/`, set `icon` in `package.json`,
and check it renders on both Marketplace themes. Do it before #85.

## #258 — background startup opens a Computor session — **DONE** (2026-08-26)

Landed on the extension's `release/2026.10` as `eb680dd` (branch
`fix/258-lazy-activation`).

The report was half right. Signing in was *already* gated on the `.computor`
marker — `extension.ts` checked for it before calling
`handleComputorWorkspaceDetected()`, so a plain folder never authenticated,
never opened a websocket and never showed a status item. What was not gated was
activation itself: `onStartupFinished` loaded the extension in every VS Code
window on the machine, which meant icon generation, a UI-state migration, three
file watchers and a hidden status bar item in windows that had never heard of a
course.

`activationEvents` is now `["workspaceContains:.computor"]`, so activation is
gated on the same thing the login always was. Everything else reaches a plain
folder through the implicit activation VS Code generates for contributed
commands, views and custom editors — which is why the `^1.74.0` engine floor is
now pinned by a test.

The marker scan also moved off `workspaceFolders[0]` and onto every folder
(`src/activation.ts`): `workspaceContains` fires for any folder of a multi-root
workspace, so looking only at the first could have woken the extension and then
found nothing to sign in to.

**Deliberately not done:** the issue also asks to strip the post-login view
focus. That focus is the remembered-container restore landed for #285 — the
whole point is that reopening a workspace returns you where you were — so
removing it would regress a shipped fix. It only ever runs after a session
starts, which in a marker workspace is the expected outcome.

**Coder is unaffected:** both code-server templates `touch` the marker
(`ops/coder/templates/vscode/startup.sh.tftpl:58`,
`matlab-vscode/startup.sh.tftpl:95`) well before they launch code-server
(:175, :266), so a provisioned workspace still comes up connected.

**One behaviour change to expect:** a student who clones their repo onto their
own laptop has no marker until their first sign-in writes one, so the first
`Computor: Login` there has to come from the command palette. Every later open
of that folder activates on its own.

**Re-test:** open a plain unrelated folder — the Computor output channel stays
empty and no `computor.*` command is registered until one is invoked from the
palette. Open a Coder workspace — unchanged, signs in and lands on the
remembered container.

## #71 — auto-open the bottom views — **PARTLY DONE**

The results half works: `ui/results/registerResultsPanel.ts:145-157` focuses
`workbench.view.extension.computor-test-results` and then the panel itself
whenever results are shown non-silently.

**Steps**

1. Confirm a *test run* takes that non-silent path — not just an explicit
   "show results".
2. Do the messages half: reveal the COMPUTOR view when a new message arrives.
3. Make it a setting. Stealing focus on every message will annoy people who
   keep the panel closed on purpose; default on, escape hatch available.

## #66 — autosave on running a test — **ALREADY DONE**

`src/commands/StudentCommands.ts:1534` registers
`computor.student.testAssignment`, and at line 1600 it calls
`await this.saveAllFilesInDirectory(submissionDirectory)` before checking for
changes, committing and testing. Submit (line 1080) and commit (line 458) do
the same.

**Steps to close:** confirm with the reporter that this is what they meant —
the issue was filed as "WIP" and a comment asks what the ask actually is. If
yes, close it.

## #149 — highlight non-committed assignments at unit/course level — **ALREADY DONE**

`ui/tree/student/StudentCourseContentTreeProvider.ts:246-276` —
`subtreeBadges()` OR-combines the dirty and unpushed badges of every assignment
in a subtree so units, including nested units, carry the glyph of whatever they
contain. The comment cites issue #332.

**Steps to close:** verify the badge also reaches the **course root** node, not
just units — the implementation walks from a node downward, so confirm the
course row is one of the nodes it is asked about. Then close.

## #140 — "Workspace Directory" cannot be selected — **PROBABLY OBSOLETE**

No such command exists in the current `package.json`; the only workspace-named
command is `computor.matlab.moveWorkspaceView`. The button in the 2025-10
screenshot appears to have been removed by the lecturer-view refactors.

**Steps:** open the current lecturer settings UI, confirm the control is gone,
and close with a note. If it is still there and still errors, it is a two-line
fix or a deletion — the issue itself asks "is it even a necessary button?".

## #253 — student progress status widget — **OPEN**

Lecturer- and tutor-facing progress views already exist
(`computor.lecturer.showCourseProgressOverview`,
`computor.lecturer.showCourseMemberProgress`,
`computor.tutor.showCourseProgress`, `computor.tutor.showMemberProgress`), so
the query work is done. What is missing is the student's own view of it.

**Steps**

1. Reuse the existing progress query rather than adding a student-specific one.
2. Show total course progress as a percentage plus a colour band against
   expected pace. "Expected pace" needs a definition — deadlines, or elapsed
   fraction of the course. Pick one and say so in the UI.
3. Put it where a lecturer can say "open X" in a session: a status-bar item
   that opens the panel is the cheapest thing that satisfies that.
4. The issue asks for it to be hard to dismiss. Resist that — make it easy to
   open and visible, not sticky. Say so on the issue rather than silently
   ignoring it.

## #122 — message tags are confusing — **OPEN, needs a decision first**

The tags render from the message kind/scope. The issue offers three options
(rename to "assignment"/"unit", or hide for students) and does not choose.

**Steps:** decide with the reporter, then it is a label map in one place. Do
not build all three.

## #123 — shift-enter to submit, title-only messages — **NEEDS DECISION**

The code deliberately does the opposite, and says why.
`webview-ui/messaging/messages-input.js:281-291`:

> Ctrl/Cmd+Enter sends (reuse the Send button); plain Enter inserts a newline.
> Enter-to-send kept posting half-written messages […]

The placeholder documents it: "Ctrl/Cmd+Enter to send". Shift+Enter already
inserts a literal newline (line 254).

The other two asks also collide with shipped decisions: the title field now
exists only on announcements (#246), where a subject is **required**
(`messages-input.js:562`), so "title only should be allowed" and "enter in
title should go to body" no longer describe the UI.

**Steps:** reply on the issue with what the composer does now and why, and ask
whether Ctrl/Cmd+Enter is acceptable. Most likely outcome is closing it. Do not
re-add Enter-to-send without a decision — it was removed for a reason.

## #126 — consistent lowercase `computor` — **NEEDS DECISION**

The concrete example in the issue is gone: there is no
`Computor: Change Backend Url` command any more, and no user-visible "Url"
casing remains (only internal command ids such as
`computor.lecturer.documents.copyPublicUrl`).

What does exist: all 220 commands are grouped under capitalised categories —
`Computor Lecturer` (52), `Computor Examples` (47), `Computor Student` (31),
`Computor` (25), `Computor Tutor` (18), `Computor Documents` (18),
`Computor Chat` (14). The package `name` is already lowercase `computor`; the
`displayName` is "Computor VS Code Extension".

**Steps:** ask whether "Computor" as a capitalised brand name in UI labels is
acceptable, given that the identifier is already lowercase everywhere. If they
want lowercase in labels too, it is a mechanical pass over the category strings
plus the display name — but it will look like a typo to users, so get the
decision on record first.

---

# Part 8 — Web UI (P2/P3)

## #144 — login input colours are hard to read — **DONE** (`fix/144-keycloak-login-theme`)

**Corrected scope.** `computor-web/app/login/page.tsx` no longer renders a
credential form — it redirects straight to Keycloak ("Keycloak is the only
identity provider — go straight there instead of showing an intermediate
button"). The screenshot on the issue predates that change (issue filed
2025-11-25; form removed in `72d8cc29`), so the credential inputs it shows no
longer exist. Credentials are typed on the **Keycloak login page** now.

**Two earlier claims in this file were wrong; corrected here.**

1. "The repo carries no theme" — it does:
   `data/keycloak/themes/computor/login/`, tracked, staged to the host by
   `computor.sh up:304-306`, with `"loginTheme": "computor"` already set in
   `data/keycloak/computor-realm.json:467`.
2. "The prod compose mounts nothing" — a misread. `docker-compose.keycloak-prod.yaml`
   is an *overlay* that only patches `command` and `KC_PROXY_HEADERS`; the
   theme volume comes from the base file and applies to prod too.

**Measured before the fix** (Playwright, live dev Keycloak, WCAG AA): the
reported symptom was already gone — credential text 18.26:1, labels 10.31:1,
title 17.74:1, button 17.74:1. What was actually broken:

- **Field errors were not styled as errors.** `#input-error` carries
  `pf-c-form__helper-text pf-m-error`; the theme only styled
  `.pf-c-alert.pf-m-danger` / `.alert-error`, which is the *page-level* alert
  and is not what a wrong password renders. "Invalid username or password."
  came out grey `#363636` at 12px — a small red icon was the only cue.
- **PatternFly's login backdrop was covered, not removed.** `kcHtmlClass=login-pf`
  paints `<html>` `#030303` plus a 47.6 KB `bg-login.jpg`, which was fetched on
  every login and then hidden under an opaque gradient on `<body>`. Stock
  Keycloak drops it in its own `css/login.css`, but this theme *replaces* that
  file (identical `styles=css/login.css` path shadows the parent's) so the
  removal was lost.
- **Nothing pinned the field's own colours** — they resolved through
  PatternFly's `--pf-c-form-control--Color`, and no `color-scheme` was declared,
  which is the standing way for a dark-set browser's autofill to reproduce the
  exact complaint.
- Labels and hints at 12px, and a `font-family: "Geist"` that this page never
  loads, so it silently fell through to Arial.

**Landed** (4 commits): danger tone + red border on `aria-invalid` fields ·
backdrop removed and the gradient moved to `<html>` · explicit field colours,
`color-scheme: light` and `-webkit-autofill` overrides · 14px labels/hints and a
font stack that resolves. All probed states now pass AA (error text 6.47:1).

**Re-test:** deploy, then sign in at the real host with a wrong password once —
the message must be red, and the two fields outlined red.

## #154 — content type colour picker offers no palette — **OPEN, confirmed**

**Verified root cause.**
`computor-vsc-extension/src/ui/webviews/CourseContentTypeWebviewProvider.ts:63`
renders a bare `<input type="color">` plus a hex text field
(lines 78-83). There are no preset swatches, which is precisely the report.

Note this provider builds its HTML as an inline string rather than using
`webview-ui/` assets, so it sits outside the shared design system.

**Steps**

1. Add a row of preset swatches above the picker, keeping the picker for custom
   values. Six to eight colours that read well against both VS Code themes.
2. Take the presets from whatever the web UI already uses for content-type
   colours (`components/progress/ContentTypeChart.tsx:26` defaults to
   `#6366f1`) so the two surfaces agree.
3. While in the file, consider moving it onto `webview-ui/` assets like the
   other webviews — optional, but it is the last inline-HTML provider.

## #161 — vanishing examples after "Filter by Tags" — **ALREADY DONE**

See `ISSUES-2026.10-STATUS.md`. Fixed by `fix/329-examples-filter-visibility`
plus #358 populating Category and Tags where the filter reads them.

---

# Suggested order

1. **Close the free ten** — `ISSUES-2026.10-STATUS.md`, after an image rebuild
   and re-test. Biggest visible movement on the board for no code.
2. **Part 1 in order**: #239 → #240 → #241 (+ the env sub-finding) → #232.
   This is the release gate.
3. **#115 → #85** — the icon unblocks the VSIX pipeline, which unblocks #363.
4. **#336** — the worst live bug outside the security bucket.
5. **#162, #150, #163** — small, confirmed root causes, real lecturer pain.
6. ~~**#351**~~ done 2026-08-26; **#350** — the status surface, still open, and
   no longer blocking anything before the workshop.
7. **#333** — the last session/credential papercut; ~~**#247**~~ and
   ~~**#257**~~ both done 2026-08-26, and #257's forced re-login does reuse
   #247's rails.
8. Part 7 and Part 8 as filler; close #66, #146, #149, #178, #234 after
   re-testing rather than building anything.

Decisions to get on record before they block work: **#179** (token strategy),
**#123** (composer keys), **#126** (casing), **#122** (tag labels), and the
#351 split between a hard licence cap and a soft capacity guard.

---
---

# Dedicated implementation plans — pickup-ready

Each plan below is self-contained: a fresh session can start from it without
re-deriving the analysis. File:line references were verified on 2026-08-26
against `b81048ec` (fullstack) and `cde5560` (extension), both on
`release/2026.10`.

**House rules that apply to every plan** (from the repo's working conventions):

- Branch off `release/2026.10`, in the repo(s) the plan names. Never push to
  `main`. Stage explicit paths only — never `git add -A`.
- Commit messages end at `Co-Authored-By:` — no session links (public repo).
- DTO changes go in `computor-types`, never in the backend package; after any
  pydantic change run `bash generate.sh` and commit the whole generated diff
  (the extension's `src/types/generated/` copy is the one hand-port exception).
- Backend exceptions: `error_code` is the FIRST positional arg — always pass
  `detail=` by keyword. Validation errors surface as **400 `VAL_001`**, not
  422. Query filters take **strings** for UUID columns and `Ltree(...)` for
  ltree columns.
- Migrations: `alembic heads` (not grep); psql via `docker-postgres-1`, port
  5437. Main postgres is 5437, Coder postgres is 5439 — never touch the wrong
  one.
- Backend test baseline with the stack up: 12 failed / 1602 passed, all 12 in
  `test_api_endpoints.py` (401s against the live API). That is not a
  regression signal.
- Stack via `./computor.sh` + `api.sh` / `web.sh`. Web uses **yarn** (v1).
  Extension unit tests: `npm run test:unit`; webview assets:
  `npm run check:assets`.

---

## Plan #239 — strip reference/spec paths from student-visible results

**Repo:** fullstack. **Branch:** `fix/239-result-path-disclosure`
**Effort:** small (half a day including the scrub).

### Root cause (verified)

Two report writers put absolute container paths into `report.properties`,
which lands verbatim in `result_json` and is returned to the student:

- `computor-testing/testers/tests/conftest_base.py:448-453`
- `computor-testing/testers/tests/octave/conftest.py:376-381`

```python
report.properties = {
    "test": testyamlfile,          # /tmp/examples/by-version/<key>/<id>/test.yaml
    "specification": specyamlfile, # /tmp/tmpXXXX.yaml (contains referenceSolution)
    "pytestflags": pytestflags,
    "exitcode": str(exitstatus),
}
```

The backend reads the report file at
`tasks/temporal_student_testing.py:518-521` and stores it unmodified at
line 588 (`result_json=test_results`).

### Steps

1. In both conftests: drop `"test"` and `"specification"` from
   `report.properties`; keep `"pytestflags"` and `"exitcode"`. Move the full
   paths to `logger.info(...)` in the same function so worker logs keep them.
2. Defensive layer in the backend, where the report is loaded
   (`temporal_student_testing.py`, right after `json.load(report_file)`):
   walk `test_results.get("properties", {})` and delete any entry whose value
   is a string starting with `/`. One tight helper, reused by the tutor
   workflow (`temporal_tutor_testing.py` reads the same report shape).
3. Scrub historic rows. One-off SQL against `result.result_json` (via
   `docker-postgres-1`, port 5437): update rows where
   `result_json->'properties'` has a `test` or `specification` key, removing
   those two keys (`#-` / `jsonb_set`). Take a count first, note it in the
   commit message. Do NOT touch anything else in the blob.
4. Tests: unit test on the backend helper (dict in → paths gone, exitcode
   kept), and a testing-framework assertion that a generated report's
   `properties` contains no value starting with `/`.

### Verify

- Run one Python and one Octave example locally
  (`computor-test python run -T … -s …`), inspect `testSummary.json`.
- With the stack up: submit, then `GET /results/{id}` as the student — no
  absolute path anywhere in the payload.

---

## Plan #240 + #241 — isolate the student subprocess (filesystem + network)

**Repo:** fullstack. **Branch:** `fix/240-241-student-sandbox`
**Effort:** the largest item in the backlog; do it as one branch, filesystem
and network together, because both hinge on the same launcher.
**Prerequisite:** #239 merged (path disclosure feeds the #240 attack).

### Root cause (verified)

- `tasks/temporal_student_testing.py:440-500`: `reference_path` (cached
  example incl. `*_master.*`) and `student_path` sit on the same filesystem;
  the tester runs as a plain subprocess of the worker — same UID `worker`,
  same `/tmp`, no namespaces. `job_config` carries `reference_path`.
- `ops/docker/docker-compose.prod.yaml:243-283` (and dev :115): the
  `temporal-worker-testing` service is on `computor-network` with default
  egress, `depends_on` postgres/redis/minio. Everything it spawns inherits
  that reachability.
- `computor-testing/Dockerfile.sandbox` documents the right recipe
  (`--network none --read-only --cap-drop ALL --pids-limit`) but nothing runs
  it; `sandbox/executor.py` is rlimits + env, not isolation.

### Architecture decision (make it first, in the PR description)

Isolate **inside** the existing worker container with user+mount+net
namespaces (bubblewrap or `unshare`), NOT nested Docker. The worker runs as
non-root with `no-new-privileges:true`; giving it a docker socket would be a
bigger hole than the one being closed. Consequences:

- setuid helpers are off the table (`no-new-privileges`); user namespaces are
  the only unprivileged route.
- **Step 0 is a runtime probe**: whether unprivileged userns works under the
  current Docker seccomp profile is host-dependent. Run
  `docker exec computor-temporal-worker-testing-1 unshare -Urn true` (and
  `bwrap --unshare-all true` once installed). If the default profile blocks
  it, add a custom seccomp profile permitting `unshare`/`clone` with
  namespace flags to the two testing-worker services only — do not go
  `seccomp=unconfined`.

### Steps

1. **Step 0**: probe as above; record the result in the PR. If userns is
   impossible on the target hosts even with a tailored seccomp profile, fall
   back to the "separate UID + 0700" variant (step 6 becomes the primary
   mechanism, network isolation moves to compose-level only) — and say so.
2. Add `bubblewrap` to `docker/testing-runtimes/Dockerfile` (apt line ~15).
   Rebuilding runtimes is expensive; coordinate with any other pending
   runtimes change.
3. Write `computor-testing/sandbox/launch.py`: given argv, a writable workdir,
   and a list of read-only binds, exec via
   `bwrap --unshare-all --die-with-parent --ro-bind <student_path> …
   --bind <output_path> … --tmpfs /tmp --proc /proc --dev /dev`
   plus the interpreter/runtime paths (`/usr`, `/lib*`, `/home/worker/.local`
   read-only). `--unshare-all` includes the net namespace — that IS the #241
   fix. Keep the existing `ResourceLimits` preexec on top.
4. Wire it where the student process is actually spawned — the language
   executors (`testers/executors/*.py` via `ctexec/base.py`), NOT around the
   whole pytest run: the test harness itself must keep reading `test.yaml`
   and the reference. The boundary is "the student's interpreter process",
   which is exactly what `PyExecutor` etc. launch. The reference directory is
   simply not in the bind list.
5. Reference values still needed by the comparison run OUTSIDE the sandbox
   (they already do — the harness evals the reference in its own namespace).
   Confirm no test type feeds `reference_path` into the student process; grep
   `dir_reference` uses in `testers/tests/` and audit each.
6. Belt-and-braces on the shared filesystem: create
   `/tmp/examples/by-version/...` sets `0700` (umask in the fetch activity,
   `temporal_student_testing.py` cache-build path). With the sandbox this is
   redundant; keep it anyway — two layers.
7. Compose second layer for #241: move the two testing workers
   (`temporal-worker-testing`, matlab worker in
   `docker-compose.matlab.yaml`) onto an additional `testing-network`; keep
   `computor-network` for temporal/API reachability this cycle (the in-sandbox
   netns already cuts the student off). Full worker-level egress lockdown can
   be a follow-up — say so in the PR rather than silently skipping it.
8. **Env hygiene (the sub-finding), same branch, separate commit:**
   - `computor-backend/src/computor_backend/testing/backends.py:258`: build an
     explicit minimal `env=` (PATH, HOME, LANG, TZ, the `R_LIBS_USER` /
     `PYTHON_TEST_EXECUTABLE` style knobs) and drop `shell=True` — the argv
     list already exists at lines 240-247, it is joined only to be re-split
     by the shell.
   - `computor-testing/ctexec/environment.py:13-68`: add `API_TOKEN`,
     `TESTING_WORKER_TOKEN` and a `COMPUTOR` prefix check to
     `BLOCKED_ENV_VARS` / `filter_env`.
   - `testers/executors/document.py:114`: justify `use_safe_env=False` in a
     comment or flip it; with the filter fixed it is defensible either way.

### Verify

Submit the issue #237/#240/#241 probes as a real student submission:

- `os.listdir("/tmp/examples")` → must fail (ENOENT — the path is not bound).
- `open(<ref path from an old result>)` → must fail.
- socket connects to `redis:6379`, `postgres:5432`, `minio:9000`,
  `8.8.8.8:53` → all must fail.
- `os.environ` dump → no `API_TOKEN`.
- Then the regression half: run the full example set of one course and diff
  every `result_value` against pre-branch results — grading must be
  bit-identical.

---

## Plan #232 — skipped tests must not reduce the grade

**Repo:** fullstack. **Branch:** `fix/232-skip-grade-erosion`
**Effort:** small-medium; the backfill decision is the only open question.

### Root cause (verified)

- `computor-testing/testers/tests/test_base.py:820`: missing reference
  variable → `pytest.skip(...)`.
- `testers/tests/conftest_base.py:949-958`: `skipped` is summed into the
  summary but `total` still includes it.
- `tasks/temporal_base.py:159-168` `extract_test_counts` ignores `skipped`;
  `tasks/temporal_student_testing.py:533` computes
  `result_value = p / max(t, 1)`.

### Steps

1. `test_base.py:820`: change to `pytest.fail("BROKEN EXAMPLE: variable `X`
   missing from the reference — fix the example, this is not a student
   error")`. A broken reference is an authoring bug and must scream, not tax.
   Check the analogous `pytest.skip(solution["errormsg"])` sites (589, 1283,
   1356) — those are *student* setup failures and stay as they are.
2. `extract_test_counts` → return `(passed, failed, total, skipped)`; update
   both call sites (`temporal_student_testing.py:533`,
   `temporal_tutor_testing.py` equivalent):
   `denominator = max(total - skipped, 1)`.
3. Degenerate guard: if `total > 0 and skipped == total`, set
   `result_value = 0.0` and a `status` that reads as inconclusive — an
   all-skipped run must not be 100%.
4. Regression tests in `computor-backend/src/computor_backend/tests/`:
   (4 total, 3 passed, 1 skipped) → 1.0; (4, 2, 1 failed, 1 skipped) → 2/3;
   all-skipped → 0.0.
5. Backfill: recompute `result_value` for stored results whose
   `result_json.summary.skipped > 0` (the counts are in the blob). Ship as a
   reviewed one-off script under `scripts/`, run it manually, report the row
   count. If you decide against recomputation, say so on the issue — do not
   leave it implicit.

### Verify

Author a throwaway example whose `test.yaml` checks a variable the reference
does not define: pre-branch it silently grades 3/4, post-branch it fails
loudly naming the variable. Then the three unit tests above.

---

## Plan #121 — "Course content not found" after Submit→Test (repro protocol)

**Repos:** both, unknown until reproduced. **Branch:** after diagnosis.
**Effort:** the repro is the work; the fix is likely small.

Two candidate fixes have landed since the report (`fix/271-submit-auto-test`,
`fix/2026.10-submit-tested-commit`), so step 1 may close it.

1. Current build, Python course: open an assignment, change a file, Submit,
   then immediately Test. Repeat ×5 (the bug smells like a race with the
   post-submit tree refresh).
2. Not reproducible → close on the board naming `b03690f6` / `bd0862c` as the
   likely fixes, in plain voice.
3. Reproducible → capture the failing request from the extension's output
   channel; the string comes from ten backend sites, the plausible one on
   this path is `api/submissions.py:247` (artifact listing by
   `course_content_id`). Compare the id sent with the id the tree held
   before Submit. Expected shape: the command captured a tree item that the
   post-submit `forceRefreshCourse` rebuilt.
4. Fix in the extension: resolve the content id at invocation time (course id
   + content path → fresh lookup), never from a captured tree item. Same
   pattern as the #162 fix below — consider doing them together.

---

## Plan #336 — assignment update never reaches students (diagnosis tree)

**Repo:** fullstack first, extension for the display fix.
**Branch:** `fix/336-update-not-released` once diagnosed.
**Effort:** diagnosis half a day with DB access; fix depends on which branch
of the tree fires.

### What the code actually does (verified — this narrows the old hypothesis)

The extension release flow is *more* correct than assumed:
`LecturerCommands.ts:2440-2450` — items classified `update` get
`POST /lecturers/courses/{id}/upgrade-versions` (which re-assigns to the
latest `ExampleVersion` and resets status to `pending`,
`lecturer_deployment.py:997-1060`), then `generateStudentTemplate` runs with
an **explicit** `course_content_ids` selection, and the explicit path in
`select_deployments_for_release` (`selection.py:25-31`) picks by id
regardless of status. So the naive "nothing was pending" story does not hold
for the *release* flow.

The classification that decides whether the item is offered as an update:
`deploymentHelpers.ts:100-190` — a `deployed` item becomes an update
candidate only if `dep.has_newer_version` is true
(`lecturer_view.py:249-297`, `_compute_has_newer_version_batch` at :333).

### Diagnosis tree — run in order, stop at the first hit

1. **Reproduce with the DB open.** Upload a new version of a deployed
   example; before touching Release, read:
   `SELECT example_version_id, version_tag, deployment_status, deployed_at
   FROM course_content_deployment WHERE course_content_id = …`, and
   `SELECT id, version_number, version_tag, storage_path FROM example_version
   WHERE example_id = … ORDER BY version_number`.
2. **Branch A — no new `example_version` row** after the upload: the upload
   path failed to register the version (MinIO upload needs the repo; check
   `api/examples.py` upload). Fix there; everything downstream is fine.
3. **Branch B — new row exists but `has_newer_version` stays false**: bug in
   `_compute_has_newer_version_batch` (lecturer_view.py:333) — check the
   comparison (`version_number` vs `version_tag` string compare) and the
   cache invalidation noted at `api/examples.py:268` ("finds all affected" —
   verify it actually fires for this course). Then the lecturer is never
   offered the update — matches "everything went without an error" since
   nothing ran.
4. **Branch C — upgrade ran (`version_tag`=1.0.3, status back to `deployed`,
   fresh `deployed_at`) but the template repo still holds 1.0.1**: the
   release wrote stale content. Instrument
   `download_example_files` (`temporal_student_template_v2.py:173`) — log
   `version.id`, `version.version_tag`, `version.storage_path` — and check
   whether `storage_path` for v1.0.3 actually contains the new files in
   MinIO. Suspects: upload writing into the old version's storage prefix, or
   the release reading `deployment.example_version` before the upgrade
   transaction was committed (both API calls come from the extension
   back-to-back; check ordering/awaits in `executeRelease`).
5. **Branch D — hover shows 1.0.3, DB shows 1.0.1**: pure display bug — the
   tree renders the example's latest version, not
   `deployment.version_tag`.

### Fix (always, whichever branch fires)

- Show the **deployed** version (`deployment.version_tag` +
  `deployed_at`) in tree hover and the Details webview, and the *available*
  latest version separately with an explicit "update available" marker. The
  conflation is why this took weeks to notice.
- Remove/condition the misleading "Cannot unassign while the status is
  deployed" banner in the Details webview — it renders on a screen where
  unassigning is not what the user is doing.

### Verify

Full lecturer loop on a dev course: upload v+1 → Release offers it as
`$(sync) update` → after the workflow, the student-template repo's directory
diff shows the new content and the DB row says the new `version_tag` with a
fresh `deployed_at`. Then the student view (after `git pull`) shows it.

---

## Plan #150 — same example in two units collides in the template repo

**Repo:** fullstack. **Branch:** `fix/150-deployment-path-collision`
**Effort:** medium (migration + assign-time logic + tests).

### Root cause (verified)

`resolve_deployment_directory` (`selection.py:50-84`) falls back
`deployment_path` → `example_identifier` → `example.identifier`; both
assign paths write `deployment_path = str(example.identifier)`
(`lecturer_deployment.py:373` update, `:412` create). Nothing anywhere
enforces uniqueness, so two contents on the same example resolve to the same
directory in the student template and the second release overwrites the
first.

### Steps

1. At assign time (both branches in `assign_example_to_content`): query the
   course's other deployments for `deployment_path` equality
   (join via `CourseContent.course_id`); on collision, suffix with the
   content's unit segment from its ltree path
   (`mathematical_constants` → `mathematical_constants-week2`), and keep
   suffixing with the content slug if still colliding. Pass path strings, not
   UUID/Ltree objects, in the filters.
2. Alembic migration: partial unique index on
   `course_content_deployment (course_id-via-content, deployment_path)` —
   since course_id lives on `course_content`, either denormalise the column
   or enforce with a trigger/exclusion the way `course_member_check` does at
   `model/course.py:332`. Pick the simpler: a unique index on
   `(course_content_id → course_id)` requires the denormalised column; a DB
   trigger mirrors existing practice in this schema. Decide in the PR, don't
   silently do both.
3. Existing data: do **not** rename directories under students. The
   migration must tolerate existing duplicates (index `WHERE assigned_at >
   <migration date>`-style guard, or validate-on-write only) — new/changed
   assignments get the discriminator, old ones keep working.
4. Student-side reverse guard: opening an assignment must resolve its
   directory through the deployment record (`deployment_path`), not by
   scanning for a directory named after the example. Grep the extension's
   `StudentRepositoryManager` / content-to-directory mapping for
   `example_identifier`-based lookups and route them through the deployment.
5. Tests: assign the same example to two units → distinct
   `deployment_path`s; release → both directories exist with full content;
   student opens both.

---

## Plan #162 — created unit invisible until hard reload

**Repo:** extension. **Branch:** `fix/162-create-content-refresh`
**Effort:** small. Good first pickup.

### Root cause (verified)

`LecturerTreeDataProvider.ts:1150-1165`: after
`apiService.createCourseContent(...)` the comment claims "Cache cleared via
API" but no clear happens, and the refresh is conditional on finding the
parent in `existingContents` — a list read **before** the create.
`createAssignment` (`LecturerCommands.ts:1234`) masks this with
`forceRefreshCourse`; `createUnit` (`LecturerCommands.ts:1128-1136`) does
not await/handle the result at all — and a unit with a custom type is
exactly the reported flow.

### Steps

1. In `createCourseContent`: unconditionally
   `this.apiService.clearCourseCache(folderItem.course.id)` then refresh the
   course node (mirror what `updateCourseContent` at :1172 already does).
   Delete the two lying comments.
2. `createUnit`: use the return value — on `undefined`, the error was already
   notified; on success rely on the provider's refresh (no double refresh).
3. Sweep the sibling mutations in the same file (`deleteCourseContent`,
   move/reorder handlers) for the same read-stale-list pattern; fix any
   found in the same commit.
4. `npm run test:unit`; then live: create a unit with a custom content type —
   it must appear immediately, no reload.

---

## Plan #163 — undeployed assignments visible to students

**Repo:** fullstack. **Branch:** `fix/163-hide-undeployed`
**Effort:** small-medium.

### Root cause (verified)

`interfaces/student_course_contents.py:43-50` filters archived content and
the #338 visibility veto (`effective_visible_predicate()`), but nothing
filters on deployment state — a created-but-never-released assignment lists
for students (name + type, no files).

### Steps

1. Extend the same `if not include_hidden:` block: for **submittable**
   content, require an existing deployment whose `deployment_status` is
   `'deployed'` (`EXISTS` subquery against `CourseContentDeployment`;
   remember: string statuses, string ids). Non-submittable content (units)
   passes through — deployment does not apply to it.
2. Deliberately reuse `include_hidden` as the switch — the docstring at
   :36-41 already defines it as "what separates a student from a staff
   member", and tutor/lecturer views pass `include_hidden=True`, so staff
   keep seeing undeployed content with no further change.
3. Check the single-content path (`get_student_course_content` /
   `student_view.py:107-119` `visible_effective`) uses the same predicate so
   list and get cannot disagree; fold "not deployed" into that computation
   rather than adding a second mechanism.
4. Empty units: confirm the extension tree collapses a unit with zero
   visible children (it should, from #338 handling); if not, that is an
   extension follow-up, note it on the issue.
5. Cache: these listings are cached per user with deployment-tagged
   invalidation (`student_view.py:175-178` tags `course_content` for
   exactly this) — verify a deploy event invalidates, so the assignment
   appears without re-login.
6. Test alongside the existing visibility tests
   (`tests/test_content_visibility.py`): student list excludes
   pending/failed/unassigned-deployment assignments, includes deployed;
   tutor view includes everything.

---

## Plan #333 — surface the Forgejo clone credential

**Repos:** extension (primary), web (secondary). **Branch:**
`feat/333-copy-clone-command`
**Effort:** small. Backend is done — do not touch it.

### Verified state

`POST /user/courses/{course_id}/provision-repository` returns `clone_token` +
`clone_username` (`api/user.py:180-210`; minted once per user/instance,
`rotate=true` escape hatch — do NOT rotate casually, it breaks every
existing clone's stored credential). The extension already consumes it
(`StudentRepositoryManager.ts:644-662`, stores via
`storeManagedForgejoToken`, builds the auth URL with
`addBasicCredentialsToGitUrl`).

### Steps

1. Extension: add `computor.student.copyCloneCommand` on the student course
   root context menu (`viewItem =~ /^studentCourseRoot\.git(Managed)/` — see
   the existing menus around `package.json:2553`). Implementation: reuse the
   provisioning call (idempotent), build
   `git clone https://<user>:<token>@<host>/<owner>/<repo>.git` with the
   existing `addBasicCredentialsToGitUrl`, write to clipboard, notify
   "Clone command copied — it contains your personal access token, treat it
   like a password."
2. Null-token case (`clone_token` is null until first Forgejo login — the
   generated type at `courses.ts:1137` documents this): the provisioning
   call itself resolves it; if still null afterwards, show the guidance
   message instead of a broken command.
3. Add one paragraph to the student help (the `docs/student-help-rewrite`
   content): under SSO there is no Forgejo password; the terminal credential
   is this token.
4. Web: the course page shows the repository — add a copy button beside it
   calling the same endpoint. Exploratory: locate the component via the
   course detail page (no dedicated repo component found under
   `src/components/courses/` — search for `provision-repository` /
   `http_url` usage first; if the web UI turns out not to render the repo
   at all, drop this half and say so on the issue).
5. Close #342 as duplicate of #333 (plain-voice comment).

---

## Plan #257 — websocket outlives its token — **DONE**

Shipped as `fix/257-ws-token-expiry` in both repos (2026-08-26). Four of the
five steps landed as written; the two corrections are noted below.

**Repos:** both. **Branch:** `fix/257-ws-token-expiry`
**Effort:** medium.

### Verified state

`websocket/auth.py` authenticated once at handshake (4001 on bad token,
lines 92/119) and refreshed only the SSO session TTL (:145). The receive
loop (`websocket/router.py:107-167`) never revisited auth; close codes in use
were the auth failures at 144/158 and 1011.

### Steps

1. ~~Backend: resolve the credential's expiry at handshake, hold it on the
   connection record, close with a dedicated 4003 when it passes.~~ Done, as
   `WebSocketCredential` + `router._watch_credential_expiry`. Two things the
   plan did not anticipate:
   - **A per-receive `asyncio.wait_for` deadline is the wrong shape.** A
     companion task is right, because the deadline has to be *re-read*, not
     counted down: an SSO session's TTL slides with every HTTP request the
     user makes, so a deadline captured at handshake would close the socket of
     someone actively working. Re-reading is also what makes a sign-out
     elsewhere close the connection.
   - **That re-read must not refresh the TTL** (`ttl`, never `expire`), or a
     connection keeps its own session alive and never expires. The same
     applies to the reauth path — see step 2.
2. ~~Optional refresh path.~~ Done rather than skipped: `system:auth_expiring`
   warns the client, which answers `system:reauth` with a renewed token and
   keeps its subscriptions. Worth the small surface — without it every session
   boundary costs a full resubscribe. It authenticates with the TTL refresh
   *off*, and refuses a token belonging to a different user: the connection's
   subscriptions were authorised against the principal that opened it.
3. ~~Extension: 4003 → refresh → reconnect, then `reportExpired`.~~ Done as
   written, plus an `activeToken` so a refresh that returns the *same* token
   is recognised as "nothing was renewed" instead of being sent to the server
   as if it were new.
4. **Dropped: `computor-web` has no WebSocket client.** Only the generated
   event types under `src/generated/types/websocket.ts`; no `new WebSocket`
   anywhere in `src/`. Nothing to give the 4003 contract to until one exists.
5. ~~Verify with a short-TTL token.~~ Done for both credential kinds — a 20s
   API token (warned t+0, closed 4003 at t+19.7s) and an SSO session deleted
   mid-connection (closed 4003 at the next re-check). Detection latency for
   the sliding case is bounded by `EXPIRY_RECHECK_INTERVAL_SECONDS` (30s).

---

## Plan #247 — token-expiry flow polish — **DONE**

Shipped as `fix/247-token-expiry-ux` (2026-08-26), merged as `a4e8a77`. All
five steps landed as written — see Part 4's entry for what each one became.
Step 3's "capture `{command, args}` at the failure site" turned out to be
better served one level up, in `commandRegistrar`: it is the only place that
already sees both, so no failure site had to be threaded.

**Repo:** extension. **Branch:** `fix/247-token-expiry-ux`
**Effort:** small-medium. Pairs naturally with #257 step 3.

1. Error taxonomy: wherever the API client maps failures, split
   "credential expired/invalid" from "backend unreachable" (#117 settled the
   latter's wording) — distinct notification titles.
2. Deep link: the notification's action opens the Settings View scrolled to
   the token entry for the failing realm (pass the realm/server id in the
   webview message), not the view root.
3. Retry the interrupted action: capture `{command, args}` at the failure
   site; after successful validation of a new token, show "Ready — retry
   <action>?" (auto-retry only if idempotent — reads yes, submits no).
4. Structure it as a small `CredentialRecoveryService` so #248
   (self-rotation) and #257's forced re-login land on the same rails later.
5. `npm run test:unit`; manual pass with a deliberately broken stored token.

---

## Plan #244 — schema-truth fixes + issue re-scope

**Repo:** fullstack (+ `computor-types`). **Branch:** `fix/244-schema-truth`
**Effort:** small for the two fixes; the re-scope is a comment.

Already resolved since the report (do not re-fix): the `my-team` 500
(module deleted by `refactor/remove-team-formation`), user delete cascade,
and an invite flow now exists (`api/invites.py`).

1. `course_group_id`: the DB requires it for `_student` members
   (`model/course.py:332` check constraint). Make the API say so — either
   declare it required-for-students in the `CourseMemberCreate` DTO
   (computor-types; conditional validator) or pre-validate in the endpoint
   with a clear 400 naming the field. Then `bash generate.sh`, commit the
   whole generated diff.
2. `predefined_token`: create accepts `minLength: 32` but auth requires
   exactly `ctp_` + 32 chars, so longer values are accepted and then fail on
   every use. Align the DTO pattern (`^ctp_[A-Za-z0-9]{32}$` — confirm the
   exact charset from the auth validator) so create rejects what auth will
   reject. Regenerate as above.
3. Verify bug #2 is gone: `POST /submission-groups` with the issue's payload
   against the current build — the provisioning refactor
   (`submission_group_provisioning.py`) likely obsoleted it. Record the
   outcome either way.
4. Re-scope the issue in a plain-voice comment: what is fixed, what remains,
   and that `seed.sh` (direct-DB fake users + enrolments, `--cleanup`) is
   the supported synthetic-student path today. The lecturer-mints-tokens ask
   is a real permission widening → separate decision issue if still wanted.

---

## Plan #262 — per-course grader grants — **DONE**, and steps 1–3 were the wrong shape

Shipped as `test/262-grading-access` (2026-08-26), not the branch named below:
nothing needed granting, so nothing was a `feat`. What actually landed is in
Part 4's corrected entry. The plan below is kept because three of its five
steps would have built a role the system already has.

> **Step 1 invented `_grader` when `_tutor` already is one.** The step hedged
> correctly — "only if the role ladder hard-codes an ordering that `_grader`
> breaks" — but checked the wrong thing. The ladder does not hard-code an
> ordering (it is fully derived from `DEFAULT_HIERARCHY`/`ROLE_LEVELS` in
> `permissions/principal.py:51-64`), so a `_grader` role *would* have slotted
> in cleanly. The reason not to is different: `_tutor` already grades
> (`business_logic/submissions.py:701`), so a `_grader` inserted below
> `_lecturer` would differ from `_tutor` by exactly one report — the
> course-member statistics matrix — and that report is deliberately a lecturer
> surface. The new role would have been a rename.
>
> **Step 2 would have lowered a floor that is correct where it is.** "Gate
> every read/write in `course_member_gradings.py` on tutor-or-above" is a real
> permission widening: that module is the course-wide progress matrix over
> every member, i.e. course management, not grading. It stays `_lecturer`.
> Grading a submission was never in that module — it is
> `create_artifact_grade`, and it was already at `_tutor`.
>
> **Step 3's "extend that endpoint's answer" was unnecessary.** Route hiding
> already works: `/user/views/{course_id}` answers `["student","tutor"]` for a
> `_tutor` (`business_logic/users.py:16-19`) and the web's grading pages render
> only under the Lecturer section (`Sidebar.tsx:131-135`), which needs the
> `lecturer` or `management` view. A grader never sees the link. (The path is
> `/user/views/{course_id}`, not `/user/courses/{id}/views` as written below.)
>
> **Steps 4 and 5 were right.** Keycloak needed no new claim, for exactly the
> reason step 4 gives. And step 5 was the only actual work: the test the issue
> names did not exist. It does now.

**Repo:** fullstack. **Branch:** ~~`feat/262-course-grader-grant`~~ →
`test/262-grading-access`
**Effort:** medium. No dependencies; can start any time.

Note the issue's file names are stale: there is no `api/grading.py` — the
surface is `api/course_member_gradings.py` plus the grading read layer
(`refactor/grading-read-layer`, `feat/2026.10-grading-page`).

1. Model the grant as a **course role**, not a new table: check how
   `_tutor`/`_lecturer` course roles are seeded (`permissions/role_setup.py`)
   and whether a `_grader` course role can slot into the existing
   `CourseMember.course_role_id` machinery. A grader is then a course member
   with role `_grader` — membership UI, permission checks
   (`check_course_permissions(..., "_grader", db)`) and the web's
   role-driven nav all come for free. Only if the role ladder hard-codes an
   ordering that `_grader` breaks (check `permission-ladder` refactor) fall
   back to a dedicated grant table.
2. Gate every read/write in `course_member_gradings.py` (and the grading
   page's queries) on tutor-or-above **or** `_grader` for that course. One
   helper, used everywhere — endpoint and UI gating must not diverge.
3. Web: hide the grading route for users without the role, driven by the
   existing `useSystemRoles()` / course-views mechanism
   (`GET /user/courses/{id}/views`, `api/user.py:120-140`) — extend that
   endpoint's answer rather than inventing a client-side check.
4. Keycloak: no new claim needed if this is a course role — the user logs in
   via Keycloak as always and the grant lives in the DB. State this in the
   PR; the issue's "reuse the Keycloak role/claim path" is satisfied by
   identity, not by a new claim.
5. Tests (`tests/test_grading_access.py` per the issue): granted member
   reaches cells; ungranted 403; other course invisible; `_grader` cannot
   write anything outside grading.

---

## Plan #185 — backend email service

**Repo:** fullstack. **Branch:** `feat/185-email-service`
**Effort:** medium.

1. Config in `.env` via settings: `SMTP_HOST/PORT/USER/PASSWORD/FROM`,
   required-if-enabled using the `${VAR:?must be set}` compose convention —
   never a default credential. An `EMAIL_ENABLED` flag; disabled = console
   transport that logs the rendered mail.
2. `computor_backend/email/` — one `EmailService` with `send(template, to,
   context)`; templates as files (subject + text body; HTML later). No
   scattered `smtplib` calls in business logic, ever.
3. Delivery through Temporal: a `send_email` activity on an existing worker
   queue (a dead relay must never block a request thread); retries with
   backoff, drop-and-log after N attempts.
4. Exactly two events this cycle: sign-up verification and invite
   (`api/invites.py` currently returns/link-only). Resist the notification
   list until these two work in production.
5. Tests: template rendering unit tests; activity test with a stub
   transport; dev smoke via the console transport.

---

## Plan #351 + #350 — capacity limits and the status surface

**Repo:** fullstack (+ web). **Branch:** `feat/351-capacity-limits` and
`feat/350-instance-status`. **Effort:** medium each.

> **#351 is DONE** (2026-08-26). The ordering claim above — "350 first, 351's
> guard wants its numbers" — was wrong: the issue asks for a hard limit
> *"in the meantime"*, before the computed one, so #351 shipped standalone.
> #350 is still open and still worth doing; when it lands it feeds the
> *computed* variant of the guard, not the one that exists.

### #350 — `GET /instance-status`

1. New endpoint in `api/instance.py` (keep `/instance-info` untouched — it
   is consent-exempt discovery). DTO in computor-types
   (`InstanceStatusGet`), then `bash generate.sh`.
2. Content: process start time, build identity (commit/tag — inject at build
   or read from an env the compose sets), host memory total/free, workspace
   count + memory attributed to workspaces (via the Coder client the backend
   already has — `CoderClient.list_all_workspaces` and container stats),
   free workspace capacity (once #351 defines it). Add `psutil` to the
   backend deps (verified: not currently a dependency).
3. Authz: authenticated users get the capacity block (they need it to
   understand a refusal); admins get the rest. Two response shapes or
   field-level redaction — pick one, document it in the DTO.
4. Web: an admin/system page section, plus the capacity line surfaced in the
   course workspace rows — those already poll live status since `b81048ec`
   (#375), so hang it on that polling loop, don't add another.

### #351 — two limits, plus the one that already exists — **DONE**, and the plan below had four wrong turns

Kept for the record. What shipped is in Part 5's corrected entry; the four
places the plan below was wrong are worth keeping, because each one would have
produced a limit that did not do what the issue asked.

**1. The `session` table is not where logins live.** Step 2 pointed at
`model/auth.py:147-151`'s partial index for active sessions. Nothing writes
that table on the login path — `business_logic/auth.py` stores
`sso_session:<hash>` in Redis and never inserts a `Session` row, so counting it
would have returned zero for every deployment and the cap would silently never
have fired. Seats are a Redis sorted set instead: member = user id, score =
last-seen epoch. That also gives the plan's own recommendation (an idle window
in minutes, configurable) for free as a `ZCOUNT`, and makes "distinct users"
rather than "sessions" the natural unit, which is what step 5 asks the tests to
prove.

The refresh point matters: seats are touched on a **Principal-cache miss**
(`permissions/auth.py`), not on every request. `AUTH_CACHE_TTL` is 900s, so an
active client refreshes its seat at least every 15 minutes — which is why the
idle window is documented as "keep above 15" and defaults to 30. A per-request
`ZADD` would have doubled the Redis traffic of the whole application for a
counter nobody reads more than once a minute.

**2. `_admin`/`_maintainer` is not the right bypass set.** `_maintainer` is a
*course* role, not a system one, so it never appears in a Principal's system
roles. The bypass is an explicit frozen set of the builtin staff roles
(`_admin`, `_user_manager`, `_organization_manager`, `_service_manager`,
`_example_manager`, `_git_manager`, `_workspace_maintainer`) plus `is_service`.
Deriving it from the `_` prefix — the obvious shortcut — would exempt everyone,
because `_workspace_user` is builtin and held by ordinary students. Service
accounts bypass deliberately: shedding the testing workers takes the course
down instead of shedding load.

**3. "Counting active workspaces" is the wrong unit.** The issue says *maximum
number of workspace **users***. A user with two workspaces has spent one seat,
and refusing them a second workspace would enforce a limit nobody asked for.
The cap counts distinct owners, and a caller already among them is admitted.

**4. The extension half of step 4 does not exist.** There is no workspace
launch path in `computor-vsc-extension` — no `/coder/workspaces` call site at
all; joining a workspace is web-only. The web half needed no work either:
`api/client.ts` already surfaces `detail` as the error message and every launch
path notifies it. What *did* need work was the **login** refusal, which the plan
did not consider: the SSO callback swallowed every exception into a redirect to
the API's own root, and `/login` bounces straight back to Keycloak, so a refused
sign-in would have looped forever. It now redirects to the client's own callback
with the message, and `/auth/success` renders it instead of retrying.

One thing the plan got exactly right: keeping `enforce_template_quota` untouched.
It is the one limit that must bind admins, and there is now a regression test
saying so.

---

## Plan #364 — disposable branch environments

**Repo:** fullstack (`ops/`). **Branch:** `feat/364-ephemeral-envs`
**Effort:** large; do after the P0s. Solo-doable, all in ops.

1. The blocker to remove first: `name: computor` in
   `docker-compose.base.yaml:12` pins one stack per host. Parameterise via
   `COMPOSE_PROJECT_NAME` / `-p computor-<envid>` from the wrapper instead
   of the hardcoded `name:` (verify every `container_name:` in the overlays
   — each hardcoded name breaks a second instance; make them
   `${COMPOSE_PROJECT_NAME}`-derived or drop them).
2. `ops/ephemeral/spawn.sh <git-ref> <envid>`: clone at ref into
   `/srv/ephemeral/<envid>`, generate a fresh `.env` (new secrets, distinct
   ports or — better — Traefik host-rule routing `<envid>.<base-domain>` so
   no port arithmetic), `./computor.sh up`, run migrations, run `seed.sh`.
   Print URL + commit + image digests.
3. `destroy.sh <envid>`: `docker compose -p computor-<envid> down -v` plus
   the checkout — and nothing else. Follow the Coder-wipe discipline: the
   script must refuse to run without an explicit envid and must never
   default to the production project name. TTL via a cron calling destroy.
4. Guard rails: refuse refs not on the org remote; never copy a production
   `.env` or volume; quota of N concurrent envs (count compose projects with
   the prefix).
5. Smoke test inside spawn: login (headless auth per the `verify` flow),
   create course, submit, run a test — fail the spawn loudly if any step
   fails.
6. Document usage in the script headers (repo convention: no standalone doc
   files).

---

## Plan #85 (+#115) — VSIX release pipeline

**Repo:** extension. **Branch:** `feat/85-release-pipeline`
**Effort:** small-medium. `@vscode/vsce` 3.6.2 is already a devDependency;
publisher is `itpcp-tugraz`.

1. **#115 first**: add `resources/icon.png` (128×128), set `"icon"` in
   `package.json`. Marketplace publish fails without it — the P2 label is
   wrong, it gates this pipeline.
2. `ci.yml`: add `release/**` to the `push` trigger list (today the release
   branch only builds on PRs — verified).
3. New `release.yml` on tag push (`v*`): the existing check job as a
   prerequisite, then `npx vsce package` → upload VSIX as a GitHub release
   asset → `npx vsce publish -p $VSCE_PAT` gated on the tag. `VSCE_PAT` as a
   repo secret; record the owner in the workflow header comment (#363 wants
   the publisher named).
4. Reproducibility: the workflow pins Node 20 and uses `npm ci`; also pin
   the vsce invocation to the devDependency (`npx --no-install vsce`) so the
   lockfile governs it.
5. Dry-run on a `v-pre` tag against a pre-release Marketplace flag before
   the real 2026.10 tag; verify install from the built VSIX in a clean VS
   Code.

---

## Plan #114 + #153 — release model, CI for the backend repo, hotfix runbook

**Repo:** fullstack. **Branch:** `chore/114-release-model`
**Effort:** the decision is yours; the wiring is a day.

1. Decide and write the model into `RELEASING` material *inside script
   headers / an existing doc location* (house rule: no new standalone docs —
   the workflow YAML header comment is a legitimate home): unstable =
   feature branches, testing = main, stable = `release/**`, hotfix =
   cherry-pick from/to stable, one release per semester with a dated freeze.
2. Reconcile with reality: today everything targets `release/2026.10` and
   `main` is stale/unwanted. Either the flip to main-as-trunk (planned
   2026-08-13, never executed — and never content-merge main→release) is
   executed as part of this, or the written model blesses release-branch
   development. Decide once, on the record.
3. Add `.github/workflows/ci.yml` to the fullstack repo (verified: none
   exists): ruff/lint, the backend suite, `yarn lint` + `npx tsc --noEmit`
   for web, extension-free. Gate: the 12 known live-API failures in
   `test_api_endpoints.py` must be excluded or fixed explicitly — a CI that
   is red on day one is worse than none.
4. Hotfix runbook as `scripts/hotfix.sh` (or documented `gh` sequence in a
   script header): branch from release tag → fix → cherry-pick to the other
   line → tag → deploy pointer. Close #153 pointing at it.

---

## Plan #258 — stop background startup from opening a session — **DONE**

**Repo:** extension. **Branch:** `fix/258-lazy-activation`, merged as `eb680dd`.

Two things in this plan turned out to be wrong when the code was read properly,
and are recorded here so the same detours are not taken again.

- **`onView:` cannot work.** Every Computor activity-bar container is
  `when`-gated on a `computor.*.show` context key that only gets set after
  login. A view that is not on screen cannot be revealed, so its activation
  event can never fire. The marker is the only usable self-activation
  condition, which is what shipped: `["workspaceContains:.computor"]`.
- **The quiet-startup test file did not exist.** There was no
  `test/extension/` directory at all, so it was written from scratch and
  `test/extension/*.test.ts` added to `.mocharc.unit.json`.

Step 3 (kill the post-login focus) was **declined**: that focus is #285's
remembered-container restore and removing it regresses a shipped fix. Step 4
(a Coder-only eager path) turned out to be unnecessary — the templates write
the marker, so Coder is covered by the marker rule like everything else.

What actually shipped is in the #258 entry in Part 7.

---

## Plan #253 — student progress widget

**Repo:** extension (+ possibly a small student endpoint).
**Branch:** `feat/253-student-progress`
**Effort:** small-medium.

1. Check what the student list payload already carries: the tree renders
   per-assignment percentages today (#354 fixed their semantics), so a
   course-level aggregate may be computable client-side from
   `CourseContentStudentList` without a new endpoint. Only add a backend
   aggregate if the client would otherwise page through everything.
2. UI: a `StatusBarItem` (precedent: `ui/StatusBarService.ts` already has
   `courseItem`/`syncItem`) showing `X%` with theme-safe color coding,
   click opens a small progress panel (existing webview machinery,
   `computor-add-webview` skill covers the plumbing; base.css only).
3. "Expected pace" needs a definition. Ship v1 as plain completion %
   (submitted+passed / deployed assignments) and leave pace-vs-deadline out
   unless the deadline data actually exists on contents — check
   `CourseContent.properties` first; do not invent a schedule model for a
   status widget.
4. Per the issue's ask that a lecturer can say "open it" in class: command
   `computor.student.showProgress` in the palette + the status bar click.
   Decline the "hard to click away" part on the issue (plain voice, one
   sentence: sticky UI punishes everyone else).

---

## Plan #144 — Keycloak login theme — **DONE**, and the plan below was wrong

Kept for the record because three of its four steps rested on a bad premise.
The theme already existed at `data/keycloak/themes/computor/login/` (not
`ops/keycloak/`), the realm already selected it, and the prod overlay already
inherits the base file's theme mount — so steps 1–3 were mostly moot. See the
corrected #144 entry in Part 8 for what was actually broken and what landed.

One deliberate departure from step 2: the theme keeps `styles=css/login.css`
and does **not** extend the stock sheet with a separate `css/computor.css`.
This is a full restyle onto computor-web's look, not a tweak on Keycloak's;
inheriting 629 lines of stock CSS would mean fighting it with `!important` and
would pull in a second background image. The cost of shadowing — you inherit
none of the stock fixes, including its removal of PatternFly's backdrop — is
now paid explicitly and commented at each site.

Step 4's verification did happen, and is the reason the real defects surfaced:
Playwright against the live dev Keycloak, computing contrast per element across
the empty form, the invalid-credential state, both `prefers-color-scheme`
settings, and a 390px viewport.

---

## Plan #154 — content-type colour presets

**Repo:** extension. **Branch:** `fix/154-content-type-swatches`
**Effort:** small.

Verified: `src/ui/webviews/CourseContentTypeWebviewProvider.ts:63` renders a
bare `<input type="color">` + hex text field (:78-83), inline-HTML provider
outside `webview-ui/`.

1. Add a swatch row (6–8 preset buttons) above the picker; clicking a swatch
   sets both the picker and the hex field. Presets chosen to read on both VS
   Code themes; align with what the web renders for content types
   (`ContentTypeChart.tsx:26` defaults `#6366f1` — put that in the set).
2. Keep the free picker and hex field for custom values; validation regex
   already there (:83).
3. Optional same-branch cleanup: move the provider onto `webview-ui/` assets
   like every other webview (`computor-add-webview` skill; then
   `npm run check:assets` — asset-path failures are silent, which is why
   the check exists). If skipped, say so in the PR.
4. Also the messages half of **#71** while in small-UX territory: reveal the
   COMPUTOR view on incoming message behind a setting (default on), and
   confirm a test run takes the non-silent focus path in
   `registerResultsPanel.ts:145-157`.

---

## Not planned here, on purpose

- **#237 / #238** — tracking + design-only this cycle (see Part 1).
- **#368** — a measurement campaign, not a code plan; follows #350.
- **#366** — its buildable slice IS #351, which is now done; the rest needs its
  own scoped issue first.
- **#176 / #179 / #236** — blocked on the #179 decision.
- **#121** has a repro protocol above instead of a fix plan.
- **Decisions before code:** #179 (token strategy), #123 (composer keys —
  code deliberately does the opposite), #126 (brand casing), #122 (tag
  labels). #351's licence-cap vs capacity-guard split is settled and shipped:
  all three limits exist side by side.
