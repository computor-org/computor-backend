# 2026.10 — issues still open on the board that are already fixed in code

Checked 2026-08-26 against `release/2026.10` in both `computor-fullstack` and
`computor-vsc-extension`. Every row below was verified by reading the code, not
by trusting the branch name.

These need an image rebuild + a re-test on the deployed instance, then a close
comment. No new code.

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

## Partly fixed — keep open, but the scope is much smaller than the text suggests

### #333 + #342 — Forgejo clone URL / token can't clone a repo
**Backend half is done. The user-facing half is missing.**

`POST /user/courses/{course_id}/provision-repository` already mints and returns
a per-user Forgejo clone token (`clone_token` + `clone_username`,
`api/user.py:180-210`). It is minted once and reused, because Forgejo keeps one
token per user per instance; `rotate=true` is the escape hatch.

The extension consumes it internally
(`StudentRepositoryManager.ts:644-662`) and clones fine. What does **not**
exist is any way for a student to *see* a working credential, so a student who
copies the clone URL out of the Forgejo web UI gets a password prompt for an
account that only ever had Keycloak — which is exactly what both issues report.

Remaining work is in the backlog under **Part 4**. Both issues are the same
root cause; close one as a duplicate of the other.

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
| #333 | partly fixed | keep open — needs a UI surface only |
| #342 | duplicate of #333 | close as duplicate |

Eleven issues closable without writing code, plus #144, #258 and #351, which
did take code. All three are listed here because the report and the code
disagreed: #144's screenshot showed a surface that was already gone, #258's
session-on-startup was already gated (only the activation underneath it was
not), and #351 looked half-implemented by a limit that turns out to be a
different limit.

#262 is the one row here that took a commit without taking a behaviour change:
the grant it asks for is a `_tutor` course membership and already worked, but
the test it names as its success criterion did not exist, so nothing stopped
the two grading floors from drifting apart later.
