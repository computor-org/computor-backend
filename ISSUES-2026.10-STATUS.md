# 2026.10 — issues still open on the board that are already fixed in code

Checked 2026-08-26 against `release/2026.10` in both `computor-fullstack` and
`computor-vsc-extension`. Every row below was verified by reading the code, not
by trusting the branch name.

These need an image rebuild + a re-test on the deployed instance, then a close
comment. No new code, except where a row says otherwise (#144, #258, #351,
#247, #257).

---

## Fully fixed — close after re-test

### #304 — tutor test runs always fail (`service_config` never passed)
**Fixed.** `api/tutor.py:48-49` imports both payload builders and
`api/tutor.py:676-677` passes `service_config` alongside `service_type_config`,
matching the student path at `api/tests.py:403-404`.
Landed as `fix/2026.10-tutor-service-config`.

**Re-test:** `POST /tutors/course-contents/{id}/test` on a course whose service
has a testing language — must no longer report
`Service '…' has no testing language configured`.

---

### #309 — `datetime.utcnow()` in workflow bodies + example-cache rewrite race
**Fixed, both halves.**

1. `tasks/temporal_student_testing.py:869,892` and
   `tasks/temporal_tutor_testing.py:390,417` now call `workflow.now()`, with a
   comment explaining why. No `utcnow()` remains in either workflow body.
2. The shared `/tmp/examples/<identifier>/` rewrite is gone. The cache is now
   immutable per version: `/tmp/examples/by-version/{version_key}/{identifier}/`
   (`temporal_student_testing.py:149-163`). Concurrent activities can no longer
   race a rewrite.

Landed as `fix/2026.10-naive-utc-timestamps` + `fix/2026.10-example-cache-race`
(291c7538).

**Re-test:** run two submissions of different versions of the same example
concurrently; both must pass and report plausible `duration_seconds`.

---

### #310 — MATLAB worker slow submissions and 45s timeouts after R2025b
**Fixed.** Merge `b5794694` carries four commits:

- `b06a0ff3` — `clearvars` instead of `clear all` between submissions (this was
  the actual cost: ~2.77s → ~0.61s per submission)
- `15448400` — default test timeout raised 45s → 180s
- `97ca2e1a` — ServiceHost spared on restart, orphaned Xvfb/fluxbox reaped
- `37372dcd` — one submission at a time, so a restart cannot kill a live test

**Re-test:** submit `itpcp.pgph.mat.simple_plot` repeatedly on the
`testing-matlab` queue; no `Engine marked as stuck` cascades.

---

### #354 — testing/submission doesn't reflect correct percentage
**Fixed.** Extension `838cd46` — "tell the test percentage and the grade apart".
The tag next to the example no longer collapses to 0% / 100%.
Backend side already carried `fix/2026.10-result-value-percent` and
`fix/321-student-result-percent`.

**Re-test:** submit a partially-correct example; the tree tag must show the real
fraction.

---

### #335 — "Update pending" is confusing
**Fixed.** Extension `e4eabf4` — the label now reads "update not deployed"
instead of "update pending", which is what the state actually means.

---

### #338 — visibility for assignments and units  (also closes #147)
**Fixed in both repos.** `feat/338-content-visibility`:

- backend: nullable `visible`, evaluated as a VETO up the tree, not a fallback
- extension `30cc282` — all three trees react to hidden content
- extension `e46553f` — a whole course can be hidden too

Grading totals were deliberately left untouched: hiding an assignment does not
change anyone's existing result.

**#147** ("Lecturer: Setting Deployed Assignments Invisible") is the same
request, filed earlier. Close it as superseded by #338.

---

### #341 — global replacer for examples
**Fixed.** Extension `168b426` — "bulk checkout, cleanup and replace across
filtered examples". Filter-scoped find/replace with a new minor version, which
is what the issue asked for.

**Re-test:** the follow-on "upload all examples" + "deploy all assignments"
actions the issue mentions — confirm those two exist end to end before closing.

---

### #161 — vanishing examples after "Filter by Tags"
**Fixed.** Two changes together:

- extension `ae3e5d0` (`fix/329-examples-filter-visibility`) — the filter no
  longer empties the view irrecoverably
- `c56f159` / `af321bdb` (#358) — Category and Tags are now actually populated
  where the filter reads them, so filtering has something to match

**Re-test:** ask Winny to redo the exact flow that lost the list.

---

### #246 — drop the Subject field for submission-group messages
**Fixed.** `MessagesInputPanel.ts:313-333` renders the subject input only when
the target scope is an announcement; conversations never get one.
`messages-input.js:550-562` stops sending `title: ''`, which used to wipe the
subject of any message that had one. Global/broadcast keeps its subject, and it
is required there.

---

### #144 — colour in the web UI login is hard to read
**Fixed, on a different surface than the issue names.** The screenshot shows
computor-web's own credential form, which was removed in `72d8cc29` — `/login`
now redirects to Keycloak. Measured on the live Keycloak login page, the
reported symptom is already gone (credential text 18.26:1).

What was genuinely broken there is fixed by `fix/144-keycloak-login-theme`
(4 commits on `data/keycloak/themes/computor/login/`): field errors rendered as
plain grey hint text, PatternFly's near-black backdrop + a 47.6 KB photo
fetched and then covered, unpinned field colours with no `color-scheme`
declared, and 12px labels.

**Re-test:** sign in at the real host with a deliberately wrong password — the
message must be red and the two fields outlined red. Needs the theme staged to
`${SYSTEM_DEPLOYMENT_PATH}/keycloak/themes` (`computor.sh up` does it) and a
Keycloak restart if theme caching is on.

---

### #258 — background startup opens a Computor session
**Fixed, and half of it was never broken.** Signing in was already gated on the
`.computor` marker, so a plain folder never authenticated, never opened a
websocket and never showed a status item. Activation was not gated:
`onStartupFinished` loaded the extension in every VS Code window on the machine
— icon generation, a UI-state migration, three file watchers and a hidden
status bar item in windows with no connection to a course.

`activationEvents` is now `["workspaceContains:.computor"]`; commands, views and
custom editors still reach a plain folder through VS Code's implicit activation
(engine floor `^1.74.0`, now pinned by a test). Marker detection also stopped
looking only at `workspaceFolders[0]`.

Landed as `eb680dd` on the extension's `release/2026.10`
(`fix/258-lazy-activation`, 2 commits + 15 unit tests).

**Re-test:** open a plain unrelated folder — nothing Computor loads until a
command is run from the palette. Open a Coder workspace — unchanged; the
templates write the marker before code-server starts. Note that a student's own
laptop clone has no marker until the first sign-in writes one, so that first
`Computor: Login` comes from the palette.

---

### #351 — limitation of amount of concurrent users
**Fixed, both limits, and neither existed before.** The survey originally
recorded this as "partly done" because `enforce_template_quota` looked like one
of the two. It is not: it caps *running workspaces per template*, models a hard
external constraint (MATLAB licence seats) and deliberately binds admins. #351
asks for two instance-wide limits that admins and maintainers bypass. All three
now exist side by side.

- `instance_settings` (new singleton table) holds `max_workspace_users`,
  `max_concurrent_logins` and `login_idle_minutes`. `null` = unlimited.
  Editable at runtime from `/admin/limits`, so the workshop can tune without a
  redeploy; `GET/PUT /system/limits` behind it (read: any authenticated user,
  since it is the explanation behind a refusal; write: admin).
- **Workspace users** caps DISTINCT users holding a running/starting workspace
  across all templates — the issue asks for "workspace users", not workspaces,
  so a user with two workspaces spends one seat. Enforced at provision, start
  and lecturer bulk-provision, sharing one Coder fleet listing with the
  template quota (`enforce_workspace_admission`).
- **Concurrent logins** caps DISTINCT signed-in users. Seats are a Redis sorted
  set keyed by user id — two tabs are one seat — taken at the SSO callback,
  refreshed on each Principal-cache miss (≤15 min, hence the 30-minute default
  idle window) and released on logout. **The `session` table was the wrong
  place**: the SSO login path writes `sso_session:<hash>` to Redis and never
  inserts a Session row, so counting that table would always have returned zero.
- Both refusals name the limit, the current number and the local-VS-Code
  alternative (linked when `EXTENSION_PUBLIC_DOWNLOAD_URL` is set). A cap of `0`
  reads as "switched off", not "full".
- Bypass is an explicit role list, not the `_` prefix: `_workspace_user` is
  builtin and held by ordinary students, so a prefix rule would exempt everyone.
  Service accounts bypass too — starving the testing workers would take the
  course down rather than shed load.

Landed as `feat/351-capacity-limits` (7 commits, 13 unit tests). Suite green:
1697 passed, 0 failed.

**Re-test:** set both limits low on the deployed instance from
`/admin/limits`. A student launching a workspace gets the 409 with the local
install link; an admin still gets through. The per-template MATLAB quota must
still refuse an admin — that one is supposed to.

---

### #262 — per-course individual grader access via Keycloak
**Fixed, by machinery that predates the issue. No new role, no new table.**

The issue asks for a grant of the shape `(user_id, course_id, role=grader)`,
enforced per course, with no global "grade everything" role. That is exactly a
`course_member` row: enrol the person on that one course with
`course_role_id='_tutor'` and they can grade there and nowhere else. Keycloak
supplies the identity, as the issue wanted; the grant itself lives in the
database, so no new claim was needed.

The issue's file list is stale — there is no `api/grading.py`. The two grading
surfaces sit at deliberately different floors, and that split is correct as it
stands:

- **`_tutor` — grading a student's submitted work.** `create_artifact_grade`
  (`business_logic/submissions.py:701`) and `check_artifact_access`
  (`:578-604`) both gate at `_tutor` in the artifact's own course. The ladder
  is inclusive, so `_lecturer`, `_maintainer` and `_owner` grade too.
- **`_lecturer` — `course_member_gradings`.** The course-wide progress matrix
  over every member (`repositories/course_member_gradings_view.py:200,266,375`)
  is a course-management report, not an act of grading, so a grader does not
  get it.

Cross-course isolation is structural rather than per-endpoint:
`CoursePermissionQueryBuilder.filter_by_course_membership`
(`permissions/query_builders.py:54-56`) constrains every membership lookup to
the courses where the caller holds the required role, so a grader on one course
cannot reach another's members, artifacts or statistics. Denial hides existence
(404) where the caller could not otherwise know the resource exists, and is a
403 where they can already see it.

Route hiding needed nothing either. `/user/views/{course_id}` answers
`["student","tutor"]` for a `_tutor` (`business_logic/users.py:16-19`), and the
web's grading pages live under the Lecturer section, which renders only for the
`lecturer` or `management` view (`Sidebar.tsx:131-135`). A grader therefore
never sees the link.

One thing was genuinely missing: the test the issue names as its success
criterion. Added as `tests/test_grading_access.py` — 16 tests against a live
Postgres, covering the granted grader reaching the work, the same grader
refused on a second course, students/outsiders refused, a lecturer grading, and
the statistics matrix staying `_lecturer` in both its list and per-member form.
All pass.

**Re-test:** enrol the grader as `_tutor` on the WSD course only. They can
grade WSD submissions; a second course stays invisible; the course-member
statistics page stays a lecturer surface.

---

### #247 — VSCode: token expiry error flow polish
**Fixed, all three acceptance boxes.** Extension `a4e8a77` (branch
`fix/247-token-expiry-ux`).

`src/services/CredentialRecoveryService.ts` is now the single answer to "a
credential just died — now what?", and every 401 surface routes through it.

- **Own title.** The backend case says the *sign-in* expired and offers
  `Sign in` / `Use API Token`; the git case names the server whose token was
  rejected. Neither says "unreachable" — that word stays with
  `BackendConnectionService.showConnectionError()`, which is what #117 settled.
  `AuthenticationErrorStrategy` no longer says "reload the window", and no
  longer *awaits* its own dialog (that await was the blocking prompt
  `probeToken`'s comment warns about).
- **Direct link.** `computor.settingsView` takes `{ section, url }`. The
  webview's `applyFocus()` expands that server's *Update* panel — or opens a
  pre-filled new entry when nothing is stored — scrolls to it, focuses the
  token input and flashes it. The realm comes from parsing the URL git quoted
  back; `URL.origin` drops userinfo, so a remote carrying its token inline
  cannot leak it into the notification or the webview.
- **No manual restart.** `commandRegistrar` — the one place that sees both the
  command id and its arguments — remembers the blocked
  `{command, args, label}` and reports it; everything else falls through to
  `showErrorWithSeverity` unchanged. After the token is replaced, the eight
  `*.refresh` reads replay silently and anything else gets a
  `Retry "<action>"?` button. Writes are never auto-run, and the retry only
  fires after `updateWorkspaceRemotes()` settles — earlier and it would
  re-authenticate with the token that just died.

Managed-Forgejo push failures keep their existing `Fix Authentication` route on
purpose: students never see that backend-minted token, so a Settings deep link
there is the dead end #318 already removed once.

`npm run test:unit` — 1053 passing, including 24 new ones pinning the two error
identities apart, the deep-link payload, the retry contract and the
token-stripping.

**Re-test:** corrupt a stored provider token, trigger a clone or push. The
notification must name that server and its button must land on that server's
token field, not the view root. Save a good token and take the offered retry.

---

### #257 — WebSocket disconnects leave clients in stale auth state
**Fixed, both halves.** Backend `fix/257-ws-token-expiry` in
`computor-fullstack`; extension `fix/257-ws-token-expiry` in
`computor-vsc-extension`.

The report's split state — HTTP answering 401 while the socket sits there
looking healthy — was exactly what the code did: `websocket/auth.py`
authenticated once at the handshake and nothing ever revisited it, so a
connection outlived the credential that opened it.

- **The handshake now resolves an expiry.** From the API token's `expires_at`
  (read off the cache `authenticate_api_token` has just populated, so no second
  DB round-trip) or from the SSO session key's own Redis TTL. It rides on the
  `Connection` record and is echoed to the client in `system:connected`. A
  credential with no expiry is left unwatched rather than given an invented
  deadline, and an unreadable cache degrades to the same — never worse than
  the old behaviour, where HTTP still enforced expiry.
- **A watchdog runs beside the receive loop** and closes with **4003**, a code
  of its own. 4001 means "your token was rejected" and needs the user; 4003
  means "it expired" and is usually fixed by a silent refresh. Collapsing them
  is why an ordinary session rollover looked like a hard auth failure.
- **The deadline is re-read, not captured.** SSO TTLs slide, so a deadline is a
  floor: an actively-working user keeps their socket for hours while an idle
  one closes on time. The re-read is deliberately non-refreshing (`ttl`, never
  `expire`) — a connection that renews its own session never expires. Signing
  out elsewhere deletes the key and closes the socket too.
- **`system:auth_expiring` / `system:reauth`** let a client re-arm in place
  instead of dropping every subscription and rebuilding it a moment later. The
  reauth path also refuses to slide the session TTL, so answering every warning
  with the same token cannot make a socket immortal; and it refuses a token
  belonging to a different user, since the subscriptions were authorised
  against the principal that opened the connection.
- **Extension:** 4003 refreshes and reconnects silently, and only after that
  stops producing a *different* token does it hand over to
  `CredentialRecoveryService.reportExpired({ kind: 'backend' })` — #247's flow,
  not a second one. A token the server has already closed us on is never used
  to reconnect; that loop is what turned a dead session into endless retries.
- **Giving up now says why.** Exhausting the five reconnect attempts used to
  leave a red status-bar item and nothing else, which is the half-alive UI the
  report describes. A close code cannot tell a dead session from a dead
  network, so one `GET /user` settles it: a 401 routes to the same re-login
  path every other 401 gives, anything else stays the network's problem.

18 backend tests + 10 extension tests. Live-checked against the dev stack both
ways: an API token expiring in 20s warned at t+0 and closed 4003 at t+19.7s; an
SSO session deleted mid-connection closed 4003 at the next re-check.

**Not done — and not needed:** step 4 of the plan wanted the same contract in
`computor-web`. There is no WebSocket client there at all, only the generated
event types; nothing to fix until one exists.

**Re-test:** sign in to the extension, leave the editor idle past the session
TTL. The status bar must recover on its own without a notification; killing the
session server-side must produce one clear "sign in again", not a silent dead
socket.

---

### #333 + #342 — Forgejo clone URL / token can't clone a repo
**Fixed, and the report is not a defect.**

Forgejo accounts are created by Keycloak OIDC auto-registration
(`docker-compose.forgejo.yaml:99`), so they have no local password, and SSH is
off (line 83) — HTTPS Basic auth is the only git transport. A hand-typed
`git clone` must therefore prompt for a password the SSO session cannot supply.
That is how OIDC-only git accounts behave; nothing is broken.

It is also off the supported path. `computor.student.cloneRepository`
(`package.json:157`) clones for the student using the token
`POST /user/courses/{course_id}/provision-repository` returns (`clone_token` +
`clone_username`, `api/user.py:180-210`, minted once per user/instance,
`rotate=true` the escape hatch), baked into the remote
(`StudentRepositoryManager.ts:644-667`).

The one real gap — nowhere for a student to *see* a working credential —
closed on 2026-08-24 (`3de36662`, refined by `a6556c50`): course page →
*Your repository* → **Working outside VS Code?** → **Check access** → username
and token, each with a copy button, under a warning that the token is a
password (`computor-web/app/courses/[id]/page.tsx:296-350`). Visible to any
course member, and `page.tsx:124` opens the disclosure on a successful call.

**Re-test:** as a student with no Forgejo password, open the course page, hit
**Check access**, and clone with the username and token it shows.

---

### #162 — created content does not appear until a hard reload
**Fixed.** Extension `fix/162-create-content-refresh`.

`LecturerTreeDataProvider.createCourseContent` carried a comment saying "Cache
cleared via API" next to no such call, and refreshed only when it could find
the new content's parent inside `existingContents` — a list it read *before* the
create, so a root-level unit never matched and nothing refreshed at all. The
course cache then kept serving the pre-create list until the window reloaded.
`createAssignment` hid this by calling `forceRefreshCourse` itself afterwards;
`createUnit` did not, and a unit with a custom type is exactly the flow the
report describes.

It now drops the course cache and refreshes unconditionally, and `createUnit`
uses the return value, so a failed create says so instead of looking like a
create that silently vanished. Four unit tests.

**Re-test:** rebuild the extension, right-click a course's Contents folder,
create a unit with a custom content type. It must appear at once.

---

### #163 — undeployed content visible in the student view
**Fixed.** Backend `fix/163-hide-undeployed`.

The student read path filtered archived content and the #338 visibility veto,
and nothing else — so an assignment created but never released listed for
students with a name and a type and no files, which is what the report shows.

`business_logic/content_visibility.py` now answers both questions in one place:
a student sees a row when it is effectively visible **and**, if it is
submittable, its deployment has completed a release. The list filters in SQL
(`student_visible_predicate`), the single `GET` uses the row-at-a-time twin, and
the unit badge re-applies the same predicate so it cannot aggregate work the
student cannot see. Staff are unaffected — everything hangs off the existing
`include_hidden` switch that tutors and lecturers already pass.

Two deliberate choices:

- The gate reads `deployed_at`, not `deployment_status == 'deployed'`. Bumping
  an example version resets the status to `pending` and a release run moves it
  through `deploying`, and during that window the students' files are still
  there from the previous release — reading the status would have yanked a live
  assignment out from under them.
- It is **not** folded into `visible_effective`. That flag means "a lecturer hid
  this" and the staff trees grey rows by it; an unreleased assignment is
  unfinished, not hidden.

A release now also invalidates the cached course-content views. It never did,
which was harmless while a release only changed a badge, and would since this
change have left a student waiting out a five-minute TTL to see work that is
already in their repository.

**Assumption worth flagging:** submittable content with *no* deployment row at
all is treated as unreleased and hidden too. There is nothing a student can do
with it — no directory, no files — but a lecturer who wants a file-less manual
assignment now has to hide it a different way. If that turns out to matter, the
rule to relax is `released_predicate`, not the plumbing.

A unit with no visible children still renders as an empty unit. That is
deliberate: a unit is never deployed, it can carry a description of its own, and
a lecturer who wants to stage a whole unit has `visible=false` from #338.

Thirteen tests, alongside the #338 ones.

**Re-test:** deploy the backend. Create an assignment, assign an example, do
**not** release, and switch to student view — nothing appears. Release it — it
appears without a re-login.

---

### #150 — same example in two units collides in the student template
**Fixed.** Backend `fix/150-deployment-path-collision` in `computor-fullstack`,
extension branch of the same name in `computor-vsc-extension`.

The report and the plan both had it slightly wrong, in opposite directions.

The plan said nothing guarded this. Something did: `assign_example_to_content`
has refused a second use of one example in a course since 2026-03-12
(`8b2c484b`, `DEPLOY_005`), as did the batch validation behind the extension's
pre-deploy check. That refusal post-dates the report, so it stopped new courses
from being corrupted — by making the lecturer's ask impossible instead of making
it work.

The ask is ordinary: the same exercise in week 2 and week 5. What must not
happen is the two contents sharing a directory, and that was the actual defect —
`deployment_path` was set to the example identifier by both assign branches, so
two contents resolved to one directory, the second release wrote over the first,
and the student's second assignment opened onto the first one's files.

So the refusal is gone and the collision is resolved in the name instead:

- `business_logic/deployment_paths.py` allocates a directory no other
  deployment of the course holds — `mathematical_constants`, then
  `mathematical_constants-week5` (the discriminator is the content's own unit
  segment), then a number. One example with one content is untouched, so
  nothing about existing courses changes.
- A version bump keeps the directory it already has. Renaming would orphan the
  old one in every student's clone.
- The release run refuses to write into a directory another content owns, and
  fails that one deployment with a message naming the other content, rather
  than silently overwriting. This is the backstop for courses assigned before
  the allocator existed — the reporter's course among them. Ownership goes to
  whoever released first, so a new assignment can never take a directory away
  from students already working in it.
- Extension: the assignment directory is resolved from the deployment record
  only. Three places fell back to the example identifier when the deployment
  had not told them a directory — which is precisely how the student opened one
  assignment onto the other's files — and the course export named its folders
  after the identifier outright, so two assignments collapsed into one folder.

**Deliberately not done:** the plan's step 2 wanted a unique constraint on
`(course_id, deployment_path)`. `course_id` is not on `course_content_deployment`
and a partial index grandfathering legacy rows cannot catch a new row colliding
with an old one, which is the only case that matters. `DEPLOY_005` stays in the
error registry, unraised, rather than churn the generated catalogues in three
repos over a removed code.

Nothing renames an existing directory anywhere in this change.

Seventeen backend tests plus two extension tests.

**Re-test:** deploy the backend, rebuild the extension. Assign one example to
two contents in different units of a course, release both, and open both as a
student. Two directories, two assignments, no duplicate error.

---

## Summary

| Issue | State | Action |
|---|---|---|
| #304 | fixed | rebuild, re-test, close |
| #309 | fixed | rebuild, re-test, close |
| #310 | fixed | rebuild, re-test, close |
| #354 | fixed | re-test, close |
| #335 | fixed | re-test, close |
| #338 | fixed | re-test, close |
| #147 | superseded by #338 | close as duplicate |
| #341 | fixed | verify the two follow-on actions, then close |
| #161 | fixed | ask reporter to re-run the flow, then close |
| #246 | fixed | close |
| #144 | fixed | deploy theme, re-test a failed login, close |
| #258 | fixed | rebuild the extension, re-test, close |
| #351 | fixed | deploy, set the limits, re-test, close |
| #262 | fixed | enrol the grader as `_tutor` on the course, re-test, close |
| #247 | fixed | rebuild the extension, re-test with a broken token, close |
| #257 | fixed | deploy the backend, rebuild the extension, re-test, close |
| #333 | fixed | not a defect — answer with where the credential lives, close |
| #342 | duplicate of #333 | close as duplicate |
| #162 | fixed | rebuild the extension, re-test, close |
| #163 | fixed | deploy the backend, re-test, close |
| #150 | fixed | deploy the backend, rebuild the extension, re-test, close |

Twelve issues closable without writing code, plus #144, #258 and #351, which
did take code. All three are listed here because the report and the code
disagreed: #144's screenshot showed a surface that was already gone, #258's
session-on-startup was already gated (only the activation underneath it was
not), and #351 looked half-implemented by a limit that turns out to be a
different limit.

#247 and #257 are the exceptions to the table's premise: they were plain
builds, not reports the code contradicted. They sit here because they land the
same way — a rebuild and a re-test before they can be closed. #257 is the only
row that also needs the backend deployed, since half of it is server-side.

#333 is the only row that is not a defect at all. SSO-only Forgejo accounts
have no password by construction, so the prompt the student hit is correct
behaviour; what was missing was somewhere to read the token instead, and that
shipped on the web course page in August.

#262 is the one row here that took a commit without taking a behaviour change:
the grant it asks for is a `_tutor` course membership and already worked, but
the test it names as its success criterion did not exist, so nothing stopped
the two grading floors from drifting apart later.

#162, #163 and #150 arrived after this file's premise and break it: all three
were real, reproducible defects, and all three took code on 2026-08-26. #150 is
the one where the board, the plan and the code all disagreed — see its row for
what was actually true.
