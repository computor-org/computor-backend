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
| #333 | partly fixed | keep open — needs a UI surface only |
| #342 | duplicate of #333 | close as duplicate |

Ten issues closable without writing code, plus #144, which did take code — it
is listed here because the surface its screenshot shows was already gone, so
the report needed correcting rather than reproducing.
