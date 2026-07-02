# Analytics Migration: `release/2026.10` → `main`

This document captures the lecturer-analytics feature as it exists on `release/2026.10`
(in the `computor-fullstack` checkout) and what is required to recreate it on `main`
(this `computor-backend` checkout, branch `feat/lecturer-analytics`).

Primary questions answered here:

1. **What data does the web UI plot?** (Part A)
2. **What data is missing from the endpoints on `main`?** (Part D)

---

## 0. Architecture of the `release/2026.10` analytics feature

Analytics on `release/2026.10` is a **standalone reporting subsystem**, not a thin set of
dashboard endpoints:

- A **refresh job** connects to a *source* Postgres (read-only account), dumps 12 tables to
  **Parquet snapshots**, and loads them into a single **DuckDB** file (`analytics.duckdb`).
- **Report endpoints** open that DuckDB file read-only and run analytical SQL. The browser
  only ever hits the backend API; the backend reads DuckDB. **The live/source DB is never
  touched by report reads.**
- **Job metadata** is stored as JSON files on disk (`<ANALYTICS_ROOT>/jobs/*.json`). No DB
  tables, no materialized views, **no Alembic migrations**.
- The **example-source** endpoint is the one exception — it fetches example files *live over
  HTTP* from a source-instance API.
- Deployment is **prod-only** (source SSH tunnel, systemd unit, `analytics-permissions` init
  service, a manual/cron `refresh.sh`). There is no scheduler, no Temporal workflow.

Crucially, the analytics grading payloads reuse the **same backend-agnostic response builder**
(`repositories/grading_read.py`, `CourseMemberGradingReadBackend` protocol) that the live
`/course-member-gradings` endpoint uses — analytics just feeds it a DuckDB-backed repo instead
of a Postgres-backed one. This is the seam that makes a live-DB reimplementation on `main`
straightforward.

---

## Part A — Data plotted in the Web UI

The feature is **table / stat-tile heavy**. There is exactly **one chart** (a hand-rolled inline
SVG). No charting library is actually used (`recharts` is in `package.json` but unused here;
the code viewer uses `highlight.js`). All `score`/`average_score` values are **0–1 fractions**
displayed ×100 as percents; `*_percentage` values are already 0–100.

### Page 1 — `/lecturer/analytics` (course index)

Grid of course cards. Source: `GET /analytics/courses` → `AnalyticsCourseAccess[]`.

| UI element | Field |
|---|---|
| Card title | `title` (fallback `path`) |
| Role pill | `role` |
| Source badge | `source_name` |
| "{n} students" | `total_students` |

### Page 2 — `/courses/[id]/lecturer/analytics` (core dashboard)

Layout: cutoff controls → KPI row → (roster ∣ student detail).

**2a. Summary KPIs** (`SummaryCards`) — 7 stat tiles. Source: `GET /analytics/courses/{id}/summary`
→ `AnalyticsCourseSummary`.

| Tile | Field |
|---|---|
| Submitted | `submitted_percentage` (+ `total_submitted_assignments`/`total_max_assignments`) |
| Graded | `graded_percentage` (+ `total_graded_assignments`/`total_max_assignments`) |
| Students | `total_students` |
| Average grade | `average_grading` |
| Latest submission | `latest_submission_at` |
| Submission cutoff | `submission_cutoff` |
| Grading cutoff | `grading_cutoff` |

**2b. Roster** (`RosterList`) — searchable, alphabetical list of **student names only** (privacy:
no scores/ids shown here). Source: `GET /analytics/courses/{id}/students` →
`AnalyticsStudentList.students` (`AnalyticsStudentCheckpoint[]`). Only `given_name`/`family_name`/
`username` are displayed; selecting a row sets `?student={course_member_id}`.

**2c. Student detail header** — from the checkpoint row:
`standard_passed`/`standard_total`, `pass_rate`, `average_score`, `student_id`, and integrity `flags`.

**2d. THE CHART — "Cumulative official submissions over time"** (`StudentTimelinePanel`)
Source: `GET /analytics/courses/{id}/students/{memberId}/timeline` → `AnalyticsStudentTimeline`.

- Chart type: cumulative **step-line curve**, hand-drawn inline `<svg viewBox="0 0 720 200">`.
- **X axis** = time (`event.occurred_at`).
- **Y axis** = running count of official submissions.
- **Filter before plotting**: `events.filter(e => e.submit === true)` — only `submit === true` events
  are plotted.
- **Overlay**: vertical dashed orange line at `submission_cutoff`.
- Fields actually plotted: `occurred_at` + `submit`. (All other `AnalyticsTimelineEvent` fields —
  `event_type`, `grade`, `status`, `path`, `title`, … — are returned but **not visualized**.)

**2e. Standard-example evidence table** (`StandardExampleTable`) — grouped by unit. Source:
`GET /analytics/courses/{id}/students/{memberId}/examples` → `AnalyticsStandardExample[]`.

| Column | Field / transform |
|---|---|
| Example | `title` + `path` (links to source viewer) |
| Score | `score` × 100 (%), red if < 60% |
| Pass | `passed` (✓/✗); "Review" if `score === null`; `—` if not submitted |
| Rounds | `test_rounds` |
| Submitted | `submitted_at` (+ "late" tag if `late`) |
| Flags | `flags[]` (`velocity`/`low_iteration`/`tutor_concern`) |
| (sub-rows) | `comments[]` (`author_role`, `text`, `created_at`) |

Client groups by `unit` (or path-prefix) and computes per-unit subtotals (attempted/passed/avg/flags).

**2f. Integrity badges** (`IntegrityBadges`) — count badges per flag kind + a "worst band" dot.
Derived client-side from example `flags[]` (or a checkpoint rollup).

**2g. Refresh control** (`RefreshControl`, lecturers only) — `POST /analytics/courses/{id}/refresh`
then polls `GET /analytics/jobs/{jobId}`; shows `status`, timestamp, and `sum(row_counts)`.

**2h. Cutoff controls** (`CutoffControls`) — two `datetime-local` inputs (submission + grading)
mapped to `submission_cutoff` / `grading_cutoff` query params on **every** analytics read.

### Page 3 — `/courses/[id]/lecturer/analytics/examples/[contentId]` (source viewer)

Tabbed syntax-highlighted code viewer. Source: `GET /analytics/courses/{id}/examples/{contentId}/source`
→ `AnalyticsExampleSource` (`files: {name, content}[]`, `title`).

---

## Part B — Endpoint inventory (`release/2026.10`, prefix `/analytics`)

| # | HTTP | Path | Response | Read role | Feeds UI |
|---|---|---|---|---|---|
| 1 | GET | `/analytics/courses` | `AnalyticsCourseAccess[]` | any (self-scoped) | Page 1, Page 2 header |
| 2 | POST | `/analytics/courses/{id}/refresh` | `AnalyticsJobStatus` | `_lecturer` | 2g |
| 3 | GET | `/analytics/courses/{id}/jobs` | `AnalyticsJobStatus[]` | `_tutor` | (defined, unused) |
| 4 | GET | `/analytics/jobs/{job_id}` | `AnalyticsJobStatus` | `_tutor` | 2g |
| 5 | GET | `/analytics/courses/{id}/summary` | `AnalyticsCourseSummary` | `_tutor` | 2a |
| 6 | GET | `/analytics/courses/{id}/students` | `AnalyticsStudentList` | `_tutor` | 2b |
| 7 | GET | `/analytics/courses/{id}/students/{mid}` | `AnalyticsStudentReport` | `_tutor` | (defined, unused) |
| 8 | GET | `/analytics/courses/{id}/students/{mid}/timeline` | `AnalyticsStudentTimeline` | `_tutor` | 2d |
| 9 | GET | `/analytics/courses/{id}/students/{mid}/examples` | `AnalyticsStandardExample[]` | `_tutor` | 2e |
| 10 | GET | `/analytics/courses/{id}/examples/{contentId}/source` | `AnalyticsExampleSource` | `_tutor` | Page 3 |

All read endpoints accept optional `submission_cutoff` / `grading_cutoff`. When omitted, the
submission cutoff defaults to `2026-06-18T22:01:00Z`; the grading cutoff stays `None`.

**Derived heuristics (backend `analytics/service.py`)** — needed to reproduce the integrity data:
- `passed` = `score ≥ 0.6`.
- flag `low_iteration` = passed AND `test_rounds ≤ 1`.
- flag `tutor_concern` = has a comment AND grade status == 2 (correction_necessary).
- flag `velocity` = steepest window of ≥3 (≤15) consecutive official submissions within 7 days.
- "standard" content = content-types whose slug/title == "standard" (else all submittable).
- checkpoint `standard_passed` counts latest grade ≥ 0.6 **or** submitted-but-ungraded.

---

## Part C — Baseline on `main`

**Present on `main` (grading stack, live Postgres):**
- `GET /course-member-gradings?course_id=…` → `CourseMemberGradingsList[]`
- `GET /course-member-gradings/{course_member_id}` → `CourseMemberGradingsGet`
- Backing it: `repositories/course_member_gradings{,_view}.py`, `business_logic/…`, the
  `CourseMemberGradingsInterface`, and a generated `CourseMemberGradingsClient.ts`.
- All underlying DB models the analytics queries need already exist: `result`, `submission_artifact`,
  `submission_grade`, `course_content{,_type,_kind}`, `submission_group{,_member}`, `course_member`,
  `course_role`, `course`, `user`, `student_profile`.

**Absent on `main`:**
- ❌ backend `api/analytics.py`, the `analytics/` package, `computor_types/analytics.py`
- ❌ the shared read builder split (`repositories/grading_read.py`) — on `main` the grading read
  logic lives inside the view repo, not behind the backend-agnostic protocol seam
- ❌ web `src/api/analytics.ts`, `src/generated/{types,clients}/…analytics…`, `src/components/analytics/*`
- ❌ the analytics pages are **stubs** ("Analytics – Coming Soon")
- ❌ no analytics router registration in `server.py`

---

## Part D — Gap analysis: data plotted vs. data available on `main`

For each block of plotted data, what `main` already provides and what must be built.

| Plotted data | Fields | On `main` today | Gap |
|---|---|---|---|
| Course cards | `title, path, role, source_name, total_students` | title/path via `/courses`; role via membership; students countable | **No endpoint.** `source_name` is snapshot-only → drop or replace with course id. Needs a course-listing endpoint (or reuse existing course list). |
| Summary KPIs | `submitted_percentage, graded_percentage, total_students, average_grading, latest_submission_at` | **Derivable** by aggregating `/course-member-gradings` list rows across students | **No summary endpoint.** Add course-level aggregation. |
| Summary cutoffs | `submission_cutoff, grading_cutoff` | Not applied — live grading layer ignores cutoffs | **Cutoff filtering missing** in the grading read path. |
| Roster | student names | Available (course members / grading list) | None. |
| Student checkpoint extras | `standard_total, standard_passed, pass_rate, average_score, late_submission_count` | **Not provided** by `course-member-gradings` | **Entirely missing.** New per-student "standard example" computation over `result`/`submission_artifact`/`submission_grade`. |
| Cumulative-submissions chart | timeline `events[].occurred_at`, `events[].submit` | **Not provided.** Data lives in `submission_artifact` (`submit`, `uploaded_at`) | **Timeline endpoint missing** (union of artifact/result/grade events). |
| Standard-example table | per-example `score, passed, test_rounds, submitted_at, late, flags[], comments[], category, unit` | **Not provided** at example granularity | **Entirely missing.** New per-example evidence query + the flag heuristics (velocity/low_iteration/tutor_concern). |
| Integrity badges | flag counts + worst_band | derived from examples | Follows from the examples endpoint. |
| Example source viewer | `files[].{name, content}` | Not exposed for analytics; example files live in local example storage (MinIO) not a remote source API | **Missing.** Reimplement against local example/deployment storage instead of the remote source API. |
| Refresh job status | `AnalyticsJobStatus`, `row_counts` | N/A | **Only needed if the snapshot model is kept.** Drop under a live-DB approach. |

**Summary of the gap:** the *progress/grading* half of the data is already computed on `main`
(via `course-member-gradings`), just not aggregated to course level nor exposed under an
`/analytics` surface, and it does not yet honor submission/grading cutoffs. The *integrity* half —
per-student checkpoints (`standard_*`, `pass_rate`, `average_score`, `late_submission_count`),
the per-example evidence table (`test_rounds`, `late`, `flags`, `comments`), the submission
**timeline**, and the **example source** viewer — is entirely absent and must be built new.

---

## Part E — Removal plan for `release/2026.10` (planning only — no code changes there)

### E.1 Delete (files that are 100% analytics)

Backend (`computor-backend/src/computor_backend/`):
- `analytics/` (whole package: `config.py`, `service.py`, `grading_repository.py`,
  `report_repository.py`, `store.py`, `source.py`, `job_store.py`, `__init__.py`)
- `api/analytics.py`
- `scripts/analytics_refresh.py`
- `tests/test_analytics_grading_backend.py`

Shared types: `computor-types/src/computor_types/analytics.py`

Web (`computor-web/`):
- `app/lecturer/analytics/` and `app/courses/[id]/lecturer/analytics/` (incl. `examples/[contentId]`)
- `src/api/analytics.ts`, `src/components/analytics/`
- `src/generated/types/analytics.ts`, `src/generated/clients/AnalyticsClient.ts`
- `e2e/analytics.spec.ts`

Ops / scripts:
- `ops/docker/docker-compose.analytics-instance.yaml`, `ops/docs/ANALYTICS.md`,
  `ops/systemd/computor-analytics-source-tunnel.service`
- `scripts/analytics-local/`, `scripts/analytics-prod/`

### E.2 Surgical edits (files with analytics mixed in)

- `computor-backend/.../server.py` — remove `analytics_router` import + `include_router`
- `computor-backend/.../settings.py` — remove the `ANALYTICS_*` settings block
- `computor-backend/.../repositories/__init__.py`, `services/__init__.py` — drop analytics exports
- `computor-backend/.../scripts/generate_typescript_interfaces.py` — drop analytics schema entry
- `computor-backend/pyproject.toml` — drop deps only analytics uses (duckdb, pandas/pyarrow — verify no other users)
- **Decide the fate of the read-layer split** introduced alongside analytics:
  `repositories/grading_read.py` / `course_member_gradings_view.py`, `view_base.py`,
  `services/course_member_grading_{read,stats}.py`, `business_logic/course_member_gradings.py`.
  These also serve the live `/course-member-gradings` endpoint, so they must **stay** (only the
  DuckDB backend implementations go).
- Web: `app/dashboard/page.tsx`, `app/page.tsx` (remove snapshot-course merge + analytics link),
  `src/components/Sidebar.tsx`/`TopBar.tsx`/`MaintenanceBanner.tsx`, `src/contexts/AuthContext.tsx`,
  `src/hooks/usePermissions.ts`, `src/generated/types/index.ts`, `e2e/fixtures.ts`,
  `playwright.config.ts`, `package.json` (drop `highlight.js`; keep/reassess `recharts`),
  `.env.local.example`, `tsconfig.json`
- Root: `.gitignore`, `startup.sh`, `ops/docker/docker-compose.prod.yaml`,
  `ops/environments/.env.common.template`

> Removal is executed **after** the `main` reimplementation is validated, so the reference
> implementation stays available while porting.

---

## Part F — Recreation plan for `main` (branch `feat/lecturer-analytics`)

**Decision (confirmed by user):** faithful port of the **snapshot architecture** exactly as on
`release/2026.10` — DuckDB store, Parquet snapshots, refresh jobs. NOT a live-DB reimplementation.
Copy the subsystem verbatim and wire it up.

**Deployment difference from `release/2026.10` (same-system source):** On `release`, the analytics
instance ran on a *separate machine* and pulled snapshots from *another machine's* postgres over an
SSH tunnel. On `main`, snapshots are taken from **this system's own backend postgres**. Concretely:
- `ANALYTICS_SOURCE_DATABASE_URL` now **defaults to the backend's own postgres connection** (built
  from `POSTGRES_*`, same as `database.py`); an explicit value still overrides (e.g. a dedicated
  read-only role). The refresh always runs read-only (`default_transaction_read_only=on` +
  `BEGIN READ ONLY`), so reusing the backend role cannot write. Implemented in `settings.py`.
- **No SSH source-tunnel** and **no separate analytics instance** — the `ANALYTICS_SOURCE_TUNNEL_*`
  settings and the `computor-analytics-source-tunnel.service` systemd unit are not needed here.
- The DuckDB snapshot still isolates the *dashboard read load* from postgres; only the periodic
  refresh job touches postgres (a chunked, read-only full-table export).
- Example-source viewer (`ANALYTICS_SOURCE_API_URL`/`_TOKEN`) is still explicit opt-in config; if
  the source view is wanted it points at this same backend's API, else it degrades to 404. (A later
  option is to read example source from local storage directly instead of via self-HTTP.)

**Ops wiring — DONE (simplified, same-system).** `docker-compose.prod.yaml` gains an
`analytics-permissions` one-shot init service (creates + chowns `raw/duckdb/jobs`) and the `uvicorn`
service gains the analytics volume, `ANALYTICS_*` env, and a `service_completed_successfully`
dependency on the init service. `ANALYTICS_SOURCE_DATABASE_URL` is passed blank → the backend
defaults it to its own `POSTGRES_*` connection (the `settings.py` guard uses `or`, so an empty
override still falls back to the local DB). `.env.common.template` documents the knobs; a simplified
`ops/docs/ANALYTICS.md` runbook replaces the two-instance/tunnel version. **No** SSH source-tunnel,
systemd unit, separate analytics-instance compose, or prod source-tunnel scripts. `docker compose
config` (base + prod) validates.

### F.0 Status

**Backend — DONE and VERIFIED.** Ported verbatim and wired; the ported test suite passes on `main`.
- New files (verbatim copies): `computor-types/.../analytics.py`; backend `analytics/` package
  (`__init__/config/service/grading_repository/report_repository/store/source/job_store`);
  `api/analytics.py`; `scripts/analytics_refresh.py`; `tests/test_analytics_grading_backend.py`;
  and the shared read-layer deps `repositories/grading_read.py`, `utils/grading_stats.py`,
  `utils/grading_status.py` (these did not exist on `main` — analytics needs the backend-agnostic
  builder + protocol they provide; added as pure additions, `main`'s existing
  `/course-member-gradings` endpoint is untouched).
- Wire-up edits: `server.py` (import + `include_router(analytics_router, tags=["analytics"])`),
  `settings.py` (`ANALYTICS_*` block), `pyproject.toml` (`duckdb==1.5.4`; `pandas`/`httpx` already
  present, no `pyarrow` needed).
- Contract verification before copying: `computor_types/course_member_gradings.py` and `grading.py`
  are **byte-identical** across branches; exceptions, `course_role_hierarchy`, and
  `check_course_permissions` all present on `main`. `duckdb 1.5.4` already installed in the venv.
- **Test result:** `pytest tests/test_analytics_grading_backend.py` → **23 passed** (run against
  `main` via PYTHONPATH shadowing, since the dev venv is wired to the fullstack checkout).

**Web — DONE (analytics only, no web-UI refactor).** Per the user's directive, `main`'s web-UI is
NOT refactored; only the analytics feature is ported, adapting the two page files where they leaned
on `release`'s broader refactor so that **zero** refactor infrastructure and **no** existing `main`
web/auth files change.
- Copied verbatim: `src/api/analytics.ts`; `src/components/analytics/*` (11 files); the examples
  source-viewer page; `src/generated/types/analytics.ts`; `src/generated/clients/AnalyticsClient.ts`
  (`main`'s generated-client infra — `api/client`, `apiClient`, `BaseEndpointClient` — matches, so
  it compiles; not registered in the clients index, matching `release`).
- Adapted (isolated, so no refactor deps are pulled in):
  - `app/courses/[id]/lecturer/analytics/page.tsx` (replaces the "Coming Soon" stub) — dropped
    `usePermissions`; `canRefresh` now derives admin from `useAuth().user` (`role`/`systemRoles`)
    plus the snapshot-role fallback. The backend still enforces refresh via `_require_course_role`,
    so this is display-only gating. `EmptyState` was already a local helper in this file.
  - `app/lecturer/analytics/page.tsx` — inlined a simple header/error/empty in place of `release`'s
    `PageHeader`/`ErrorBanner`/`EmptyState` shared components. Course-card rendering unchanged.
- Wire-up: `src/generated/types/index.ts` (`export * from './analytics'`); `package.json` +
  `yarn.lock` (`highlight.js@11.11.1`, for the code viewer).
- Deliberately NOT ported (would be web-UI refactor or unrelated): `PageHeader`/`Breadcrumbs`/
  `ErrorBanner`/`EmptyState` shared components, the `usePermissions` hook, the `AuthContext`/`scopes`
  rework, and the ancillary `release` touches (dashboard snapshot-course cards, top-level nav
  changes, demo mode wiring, e2e/playwright fixtures). `main` already has a Sidebar link to
  `/courses/[id]/lecturer/analytics`.
- Static verification (done): every shared import used by the analytics web resolves to an existing
  `main` file; `useAuth()` exposes `user`/`isAuthenticated`/`isLoading`; `AuthUser` has
  `role`/`systemRoles`; no `usePermissions`/`PageHeader`/`ErrorBanner`/`EmptyState`-component imports
  remain. `tsc` verification pending a `yarn install` in `computor-web` (no `node_modules` on `main`).

### F.1 Deltas vs. `release/2026.10` under the live-DB approach

- **Dropped endpoints:** `POST /analytics/courses/{id}/refresh`, `GET /analytics/courses/{id}/jobs`,
  `GET /analytics/jobs/{job_id}` (no snapshot to refresh). The web `RefreshControl` and job-status
  UI are removed. `AnalyticsJobStatus`/`AnalyticsRefreshRequest` DTOs are retained (harmless, keeps
  the generated-types contract stable) but unused; `latest_job` fields serialize as `null`.
- **`AnalyticsCourseAccess.source_name`** has no meaning live → set a constant (e.g. `"live"`).
- **Cutoffs** become plain SQL filters (`... <= :submission_cutoff` on submission time,
  `graded_at <= :grading_cutoff` on grades) instead of snapshot-time defaults. Default = no cutoff
  (do **not** carry over the hard-coded `2026-06-18` default).
- **Example source** is served from the **local example/deployment storage (MinIO)** via the
  existing example-download path, not a remote source-instance API. (`ANALYTICS_SOURCE_API_*`
  settings are not needed.)
- **Permissions** reuse `check_course_permissions(permissions, CourseMember, "_tutor"|"_lecturer", db)`
  already on `main` (the snapshot-role fallback is dropped — there is no snapshot).

### F.2 Build sequence (seam-accurate)

1. **DTOs** — `computor-types/.../analytics.py` ported verbatim. ✅ *Done, compiles + imports on main.*
2. **Integrity repository** — new `repositories/analytics.py` (`AnalyticsRepository(db)`), live-Postgres
   SQLAlchemy re-implementation of the release DuckDB queries:
   - `get_student_checkpoint_rows(course_id, cutoffs)` — per-student `standard_total/standard_passed/
     pass_rate/average_score/late_submission_count` over `result`/`submission_artifact`/`submission_grade`,
     using the "standard" content-type selection rule.
   - `get_timeline_events(course_id, member_id, cutoffs)` — union of artifact/result/grade events
     (drives the cumulative-submissions chart; only `occurred_at`+`submit` are plotted, but return
     the full event per the DTO).
   - `get_student_examples(course_id, member_id, cutoffs)` — per-example score/passed/test_rounds/
     late/submitted_at/comments rows.
3. **Service** — new `services/analytics.py` (or `analytics/service.py`): the pure-Python heuristics
   (ported verbatim, no DB): `passed = score ≥ 0.6`; `low_iteration` = passed AND `test_rounds ≤ 1`;
   `tutor_concern` = comment AND status == 2; `velocity` = steepest ≥3/≤15 window within 7 days;
   checkpoint assembly; course-summary aggregation over the grading list.
4. **Grading reuse** — `summary` + `students` (grading half) call the existing
   `CourseMemberGradingsViewRepository.list_course_member_gradings(...)`; `student_report.grading`
   calls `get_course_member_gradings(...)`. Map `CourseMemberGradingsList` → checkpoint progress
   fields; total_graded = Σ `by_content_type[].graded_assignments`.
5. **Router** — new `api/analytics.py` (`APIRouter(prefix="/analytics")`, `_require_course_role`
   gate), register in `server.py` next to `course_member_gradings_router`.
6. **Example source** — reuse the existing example-download/deployment path to return
   `AnalyticsExampleSource`.
7. **Codegen** — regenerate `computor_types` TS types + `AnalyticsClient.ts` (offline codegen).
8. **Web** — port `src/api/analytics.ts` + `src/components/analytics/*` + the three pages
   (replacing the "Coming Soon" stubs), minus `RefreshControl`/job-status UI.
9. **Tests** — port the pure-heuristic tests; add live-DB query tests against a seeded course.

### F.3 Progress so far on this branch

- `docs/analytics-migration.md` (this file)
- `computor-types/src/computor_types/analytics.py` (DTOs, verified)

Everything from F.2 step 2 onward is pending — those steps need a running backend + seeded DB to
validate iteratively, and should proceed once the architecture above is confirmed.
