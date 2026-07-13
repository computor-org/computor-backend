# 08 — Web E2E (Playwright, `computor-web/e2e/`)

Decision: **expand the mocked suite now** (fast, hermetic, no stack); a thin `live`
project against the integration stack is a later phase (P8). The one existing spec
(`admin-users.spec.ts`) proved the pattern — sessionStorage auth injection +
`page.route` network mocks; this plan industrializes it.

## 1. Shared fixtures — `e2e/fixtures.ts` (finally making the README true)

Both `playwright.config.ts` and `README.md` already claim this file exists. Create it
with the pieces every spec re-implements today:

- `injectAuth(page, user)` — writes `auth_user` / `auth_provider` sessionStorage keys
  (contract: `src/services/authStorage.ts`); canned users exported as
  `PERSONAS.admin | userManager | lecturer | tutor | student` mirroring the backend
  personas (same `systemRoles` / role shapes as [03](03-personas-and-scenario.md)).
- `mockApi(page, handlers)` — one `page.route('${API_ORIGIN}/**')` with a small
  path+method router; default handlers for the always-called endpoints (`/user`,
  `/user/views`, `/user/scopes`, `/messages*`) so specs only declare what they test.
- Data builders: `buildUsers(n)`, `buildInvites(n)`, `buildCourses(n)`,
  `buildMembers(n)`, `buildExamples(n)` — typed against `src/generated/` DTOs so
  backend DTO drift breaks the build, not the runtime.
- Refactor `admin-users.spec.ts` onto the fixtures (proves the extraction).

## 2. Tooling

- Add `package.json` scripts: `"typecheck": "tsc --noEmit"` (yarn; **never npm** —
  yarn v1 lockfile) and keep `test:e2e`.
- CI-shaped local loop: `yarn typecheck && yarn test:e2e`.

## 3. Coverage plan (mocked project) — new specs in priority order

| Spec | Page(s) | What it locks down |
|---|---|---|
| `invites-admin.spec.ts` | `/admin/users/invites` | list + status badges (Active/Expired/Used/Revoked), create modal (email restriction, expiry, max uses, `SystemRoleCheckboxes`), copy-link URL shape `/invite/{token}`, revoke via ConfirmDialog; forbidden for non-`_user_manager` |
| `invite-accept.spec.ts` | `/invite/[token]` (unauthenticated) | valid-token form (prefilled restricted email read-only), password mismatch/min-length client validation, accept success → "Continue to sign in", invalid/expired token state, FastAPI `{detail}` error unwrap |
| `courses.spec.ts` | `/courses`, `/courses/create` | list, create panel (FormPanel pattern), git step shows **Forgejo** (no GitLab-type assertions — excluded) |
| `members-groups.spec.ts` | `/courses/[id]/management/members`, `…/groups` | roster, add-member flow, **student requires group select**, role ceiling surfaced (tutor option disabled/absent for plain lecturer) |
| `examples.spec.ts` | `/examples`, `/examples/upload`, `/example-repositories` | browse/upload UI (upload = mocked POST; no file editing — VSCode's job) |
| `role-dashboards.spec.ts` | `/courses/[id]/student/assignments/*`, `/courses/[id]/tutor/*` | student sees own results/grades; tutor grading view renders submissions with states |
| `git-servers.spec.ts` | `/admin/git-servers*` | list/create with `forgejo` default; admin/org-manager gate |
| `login-redirect.spec.ts` | `/login` | auto-redirect to Keycloak SSO URL (mocked), fallback link |

Out of scope by policy: `/workspaces*` (Coder), GitLab-specific UI branches.

## 4. Later — `live` Playwright project (P8)

A second project in `playwright.config.ts` (`projects: [{name:'mocked'}, {name:'live'}]`,
live excluded from the default run):

- Targets the running integration stack (`E2E_API_URL=http://localhost:18000`, web
  built against it), **real Keycloak browser login** (form fill — the one thing the API
  harness can't cover), then one golden-path slice: lecturer sees the course, student
  sees an assignment with a result, tutor sees the grading view.
- Personas/state come from the integration harness's seeded session (run after
  `make up` + suites, or a dedicated `make seed`).
- Explicitly small: it's a smoke tier, not a second matrix — deep behavior stays in the
  mocked project and the API suites.

## 5. Definition of done (mocked phase)

- `e2e/fixtures.ts` exists and `admin-users.spec.ts` uses it (README/config no longer
  lie).
- The 8 specs above pass headless via `yarn test:e2e` with no backend running.
- `yarn typecheck` passes and is wired into the docs/CI plan
  ([09-ci-and-tooling.md](09-ci-and-tooling.md)).
