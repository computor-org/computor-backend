# 03 — Personas and the Golden-Path Scenario

The scenario exercises the platform the way real users do: every action goes through the
public API with the acting persona's own token (the same endpoints the VSCode extension
calls). It doubles as the seed for the permission-matrix and contract suites.

## Personas

| Persona | System role(s) | Course role | Created by | Purpose |
|---|---|---|---|---|
| `admin` | `_admin` | — | env bootstrap (`API_ADMIN_EMAIL`/`_PASSWORD` → Keycloak group `administrators`; first login grants `_admin`) | bootstrap key-role users |
| `uma` | `_user_manager` | — | admin invite (`roles:["_user_manager"]`) | creates invite links for everyone else |
| `orga` | `_organization_manager` | — | admin invite | builds org → family → course; seats lecturer & tutor |
| `exma` | `_example_manager` | — | admin invite | uploads the Python examples (`example:upload` is example-manager-only — neither org-manager nor lecturer may) |
| `lena` | — | `_lecturer` | user: `uma` invite; membership: `orga` | authors the course: groups, students, contents, example assignment, release |
| `tobi` | — | `_tutor` | user: `uma` invite; membership: `orga` (**not** `lena` — ceiling rule) | grades students |
| `s-correct` | — | `_student` | user: `uma` invite; membership: `lena` | submits `localTests/correctSolution` for all assignments |
| `s-empty` | — | `_student` | user: `uma` invite; membership: `lena` | submits empty stubs for all assignments |
| `s-mixed` | — | `_student` | user: `uma` invite; membership: `lena` | correct for half the assignments, empty for the rest |

Two deliberate deviations from the informal spec, both forced by backend rules:

1. **The org-manager creates the course and seats `tobi`** — `course:create` is an
   org-manager claim, and the role-assignment ceiling
   (`get_course_assignment_ceiling`, `permissions/principal.py:333-357`) caps a plain
   `_lecturer` at enrolling `_student`s. The matrix asserts the denial explicitly
   (lecturer seats tutor → 403). `lena` authors everything *inside* the course.
2. **An `_example_manager` persona uploads examples** — `example:upload` belongs to
   `_example_manager` only (`permissions/role_setup.py:102-127`); org-manager has
   read-only example claims. Fits "the admin creates a few key-role users".

## Fixture data

`computor-testing/examples/itpcp.pgph.py/` — all **6** Python examples have
`localTests/correctSolution/`:
`datentypen`, `dict_und_json`, `lambda`, `slogic`, `vector_field`, `vector_random`.

Each example: `meta.yaml` (identifier, `properties.studentSubmissionFiles`,
`executionBackend.slug: itpcp.exec.py`), `test.yaml`, student stub (e.g. `datentypen.py`),
reference `*_master.py`, `content/index.md`, `localTests/{correctSolution,…}`.

`s-mixed` split (fixed, not random): correct → `datentypen`, `dict_und_json`, `lambda`;
empty → `slogic`, `vector_field`, `vector_random`.

## Golden path — numbered endpoint script

### Phase 0 — Bootstrap & onboarding (suite `02_auth`, reused as session fixture)

1. `admin` logs in (headless dance, [02-architecture.md](02-architecture.md) §4) —
   first login mints the `_admin` UserRole.
2. `admin` → `POST /admin/invites` ×3 with `{email, max_uses:1, expires_in_days:7,
   roles:[…]}` for `uma`(`_user_manager`), `orga`(`_organization_manager`),
   `exma`(`_example_manager`).
3. Each accepts: `POST /invites/{token}/accept` `{given_name, family_name, email,
   password}` (public, creates Keycloak login + computor User + UserRole rows), then
   logs in.
4. `uma` → `POST /admin/invites` ×5 (no roles) for `lena`, `tobi`, `s-correct`,
   `s-empty`, `s-mixed`; each accepts + logs in.

### Phase 1 — Hierarchy & course (suite `06_release`, first half)

5. `orga` → `POST /organizations` (path `it.org`).
6. `orga` → `POST /course-families` `{organization_id, path:"it.family", title}`.
7. `orga` creates the course **with Forgejo binding at creation** (binding locks once
   materialized — never edit afterwards):
   - `GET /git-servers` → find the auto-registered managed Forgejo (`managed:true`);
   - either `POST /courses` then immediately `PUT /courses/{id}/git`
     `{delivery:"git", git_server_id, student_repo_modes:["forgejo"]}`,
     or `POST /system/deploy/courses` with a `GitServerBinding` (async Temporal path).
     Pick ONE as canonical in implementation (recommend the sync pair: deterministic,
     no workflow polling); the other is covered by a contract test.
   - `GET /courses/{id}/git` asserts `configured/locked` state.
8. `orga` → `POST /course-members` `{user_id:lena, course_id, course_role_id:"_lecturer"}`
   and `{user_id:tobi, …, course_role_id:"_tutor"}`.
   Matrix side-assertion: the same call by `lena` for a tutor → **403**.

### Phase 2 — Examples (suite `05_examples`)

9. `exma` → `POST /examples/upload` per example: `{repository_id, directory, files}` —
   file-map with `meta.yaml` as raw text + others base64, or a single `.zip` member
   (both server-supported; implement the ZIP path — it matches how examples ship).
   Repository = the seeded MinIO `example_repositories` entry.
10. Assertions: `GET /examples` lists 6; `GET /examples/{id}/versions` shows the
    `version_tag`; `GET /examples/{id}/download` round-trips.
    Side-assertions: `lena` upload → 403; `orga` upload → 403 (read-only claims).

### Phase 3 — Course authoring & release (suite `06_release`, second half)

11. `lena` → `POST /course-groups` `{course_id, title:"it-group-1"}`.
12. `lena` → `POST /course-members` for the three students
    (`course_role_id:"_student"`, **`course_group_id` required** —
    `course_member_check` constraint; omission is a contract-suite case).
13. `lena` → `POST /course-contents`: one unit (non-submittable kind) + 6 assignments
    under it (`course_content_type_id` of a submittable kind, ltree paths
    `it.unit.datentypen` …). Auto-provisions submission groups per student per
    assignment (background task on create).
14. `lena` → `POST /lecturers/course-contents/{id}/assign-example`
    `{example_identifier, version_tag}` for each assignment
    (creates a pending `CourseContentDeployment`).
15. `lena` → `POST /system/courses/{id}/generate-student-template` `{}` (all pending)
    → `{workflow_id}`; poll release status / workflow until done
    (Temporal `generate_student_template_v2` pushes the student-template repo).
16. Assert via **Forgejo API** (admin token): template repo exists, contains the 6
    assignment directories with student stubs but **no** `*_master.py` / `test.yaml`
    leakage.

### Phase 4 — Student work (suite `07_student_workflow`)

Per student, per assignment:

17. `POST /user/courses/{id}/provision-repository` → one-time `clone_token` +
    `clone_username`; **actually `git clone`** the returned URL (public-host rewrite must
    make this work from the host) and assert the template content arrived. Re-call
    → idempotent (fresh token, same repo).
18. Resolve `submission_group_id` from `GET /students/course-contents` (per assignment).
19. Build the solution ZIP:
    - `s-correct`: files from `localTests/correctSolution/`;
    - `s-empty`: the untouched student stub (empty solution);
    - `s-mixed`: per the fixed split above.
20. `POST /submissions/artifacts` (multipart: `submission_create`
    `{submission_group_id, submit:true}` + ZIP) → artifact.
21. `POST /tests` `{artifact_id}` (≥1s spacing — `RATE_003`) → result;
    poll `GET /tests/status/{result_id}` until terminal.
22. Assert per case: `s-correct` results pass (status FINISHED, full score in
    `result_json`); `s-empty` fail/zero; `s-mixed` per split.
    Side-assertions: a student `GET`ting another student's artifact → 403/404;
    exceeding `max_test_runs` → contract-suite case.

### Phase 5 — Grading (suite `08_full_lifecycle`)

23. `tobi` → `GET /tutors/submission-groups?course_id&has_ungraded_submissions=true`
    → all 18 (3 students × 6 assignments).
24. `tobi` downloads one artifact (`GET /submissions/artifacts/{id}/download`) — spot
    check content.
25. `tobi` grades each student × assignment:
    `PATCH /tutors/course-members/{cm}/course-contents/{cc}` with `TutorGradeCreate`:
    - passing → `{grade:1.0, status:CORRECTED}`;
    - failing → `{grade:0.0, status:CORRECTION_NECESSARY, feedback}`.
    (`GradingStatus`: 0 NOT_REVIEWED, 1 CORRECTED, 2 CORRECTION_NECESSARY,
    3 IMPROVEMENT_POSSIBLE — `computor_types/grading.py`.)
26. Final assertions ("show what happened"):
    - `GET /course-member-gradings?course_id=…` — `s-correct` ≈ 100%, `s-empty` ≈ 0%,
      `s-mixed` ≈ 50%;
    - as each student: `GET /students/course-contents` reflects own grade + status;
    - `reporting.py` renders the grading-outcome table (student × assignment:
      submitted / test result / grade / status) into `reports/latest.md`.
    Side-assertions: `s-correct` grading `s-empty` → 403; `tobi` creating course
    content → 403/404 per convention.

## Where each step is asserted

| Steps | Suite |
|---|---|
| 1–4 | `02_auth` (+ session fixtures reused everywhere) |
| 5–8, 11–16 | `06_release` |
| 9–10 | `05_examples` |
| 17–22 | `07_student_workflow` |
| 23–26 | `08_full_lifecycle` |
| side-assertions | `03_permissions` (matrix rows) & `04_contracts` (payload/exception) |
