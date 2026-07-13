# 04 — Permission-Matrix Testing

Goal: every API endpoint has a declared expectation of **which role gets which status**,
asserted mechanically, with a guard that flags endpoints nobody declared. The existing
`integration-tests/fixtures/permission_matrix.py` already has the right shape — this
extends it from ~18 rows to full coverage; it does not replace the design.

## 1. Building blocks (existing, kept)

- `MatrixRow(method, path, expected: {role → status}, body?)` — one row per
  endpoint(-variant); `path` may contain placeholders resolved from the seeded scenario
  objects (`{course_id}`, `{artifact_id}`, …).
- Per-role spec files in `suites/03_permissions/` — each a one-line parametrization of
  the shared `MATRIX` with that role's session client.
- Observations recorded via `record_property("matrix_observation", …)` and rendered as
  an endpoint × role cross-tab in `reports/latest.md` by `reporting.py`.

## 2. Role axis (updated)

Old axis (`admin, owner, maintainer, lecturer, tutor, student, anon`) maps onto the new
personas; add the system-role personas since key flows now depend on them:

`admin, uma (_user_manager), orga (_organization_manager), exma (_example_manager),
lena (_lecturer), tobi (_tutor), s-correct (_student), anon`

(Course `_owner`/`_maintainer` rows can be added later if a persona is seeded for them;
the ceiling cases below cover the interesting maintainer-vs-lecturer boundary from the
org-manager side.)

## 3. Status conventions (documented once, asserted everywhere)

| Case | Expected |
|---|---|
| Unauthenticated (`anon`) on any protected route | **401** |
| Denied mutation on `organizations`, `course-families` | **403** |
| Denied action on course-and-below resources (courses, contents, members, submissions…) | **404** — existence is hidden from non-members |
| Consent gate (if enabled) | 403 + `error_code: AUTHZ_006` |
| Role-ceiling violation (e.g. lecturer seats tutor) | **403** |
| Validation failure (malformed body) | **400** + `VAL_001` — contract suite's territory, but matrix rows must not accidentally trip it (bodies must be valid) |

## 4. Endpoint inventory — generated, not hand-listed

Hand-maintained row lists rot. Instead:

1. A session fixture obtains the endpoint inventory from **`GET /openapi.json`** of the
   running stack (same source `generate.sh` uses offline via `app.openapi()`): every
   `(method, path)` + tags.
2. `fixtures/permission_matrix.py` holds the **curated expectations** (the `MATRIX`).
3. A **coverage-guard test** diffs inventory vs matrix:
   - endpoints in a committed `EXCLUDED` list (coder routes, gitlab-legacy routes,
     worker-only routes like result PATCH, websockets/SSE if any) → skipped, but the
     exclusion list itself is asserted non-stale (an excluded path that vanishes from
     the inventory fails the guard);
   - endpoints in neither `MATRIX` nor `EXCLUDED` → the guard **fails** with the list.
     New endpoints therefore force a conscious matrix/exclusion decision at PR time.

## 5. Coverage targets by router group

| Group (prefixes) | Rows to declare | Notes |
|---|---|---|
| Auth & identity: `/auth/*`, `/user`, `/api-tokens` | full | `/auth/providers` public; token lifecycle |
| Invites: `/admin/invites*`, `/invites/{token}*` | full | create/list/revoke = admin+`_user_manager` only; public GET/accept for `anon` **200/201** |
| Users & roles: `/users*`, `/user-roles*`, `/roles`, `/role-claims`, ban endpoints | full | `_user_manager` full; `_admin`-role grant by non-admin → denied (`permissions/core.py:110-113`) |
| Git servers: `/git-servers*` | full | admin + `_organization_manager` only |
| Hierarchy: `/organizations*`, `/course-families*`, `/courses*`, `/courses/{id}/git` | full | 403-vs-404 boundary lives here; delete-with-children → 409 (contract suite) |
| Course ops: `/course-members*`, `/course-groups*`, `/course-contents*`, `/course-member-import/*` | full | ceiling cases below |
| Examples: `/examples*`, `/example-repositories*` | full | upload = `_example_manager`; org-manager read-only |
| Deployment/release: `/lecturers/*`, `/system/courses/{id}/generate-student-template`, `/course-families/{id}/deploy-course` | full | lecturer-cohort gates |
| Student surface: `/students/*`, `/user/courses/{id}/*` (git, repository, provision, template-access) | full | membership-gated; cross-student isolation |
| Submissions & testing: `/submissions/*`, `/tests*`, `/results*` | full | students: own group only; tutor+: all in course; worker-only writes → `EXCLUDED` or service-token rows |
| Grading: `/tutors/*`, `/course-member-gradings*` | full | tutor+ read; grade PATCH tutor+; gradings list lecturer+ |
| Lookups: `/course-roles`, `/languages`, `/course-content-kinds`, `/course-content-types` | list-read rows | readable by any authed user |
| Excluded: `/coder/*`, gitlab-legacy (`/user/courses/{id}/register-gitlab`, sync-gitlab), worker callbacks | `EXCLUDED` list | with a comment naming the policy (no Coder testing; Forgejo-only) |

## 6. Ceiling & relationship cases (explicit named rows, not just CRUD)

These encode the decisions that shaped the scenario:

| Case | Actor → action | Expected |
|---|---|---|
| Lecturer seats `_student` | `lena` `POST /course-members` (role `_student`) | 201 |
| Lecturer seats `_tutor` | `lena` same (role `_tutor`) | **403** |
| Lecturer seats `_lecturer` | `lena` same | **403** |
| Org-manager seats `_tutor`/`_lecturer` | `orga` | 201 (uncapped, treated as `_owner`) |
| Member self/peer removal rules | per `guard_course_member_delete` | 403 |
| Student reads another student's artifact | `s-correct` → `s-empty`'s artifact | 403/404 |
| Tutor authors course content | `tobi` `POST /course-contents` | 403/404 per convention |
| Lecturer uploads example | `lena` `POST /examples/upload` | 403 |
| Import ceiling | `lena` `POST /course-member-import/{id}` with tutor rows | 403 |

## 7. Definition of done

- Coverage guard passes with zero undeclared endpoints.
- The cross-tab in `reports/latest.md` renders the full matrix.
- The 403-vs-404 convention is stated in one place (this doc + a docstring in
  `fixtures/permission_matrix.py`) and every row conforms.
