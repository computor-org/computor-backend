# Refactoring Plan: Web App (computor-web)

**Scope:** `computor-web/` — `app/` (App Router pages) and `src/` (api, clients, components, config, contexts, generated, hooks, interfaces, services, types, utils)
**Reviewed:** 2026-07-07 (branch `release/2026.10`)
**Total LOC:** ~17,300 hand-written TS/TSX (excl. `src/generated`: 14,353)

## Architecture context (read first)

- Next.js App Router, 69 `page.tsx` routes — **every page is `'use client'`**; effectively a client-rendered SPA behind cookie auth (`app/layout.tsx` mounts `AuthProvider` + `NotificationProvider`). No route-level `loading.tsx`.
- **Four HTTP layers coexist:** (1) `src/api/client.ts` `APIClient` class (backs `src/generated/clients/*` and hand-written `src/clients/*`), (2) `src/utils/apiClient.ts` `apiFetch/apiGet/apiPost` (raw Response), (3) `src/utils/api.ts` typed `api.get/post/...` wrapper, (4) raw `fetch()` in auth services and `app/page.tsx`. 401-refresh + consent-gate logic is implemented independently in layers 1 and 2. `/auth/refresh` is called from 4 different places, coalesced only by `src/utils/tokenRefresh.ts`.
- Data fetching in pages is split three ways: `useResource` hook (23 files), hand-rolled `useEffect`/`useState(true)` machines (~24 pages), and mixed.
- Type sources: `src/generated/types` (canonical, 86 imports), plus hand-written `src/types/workspaces.ts` manually mirroring backend Pydantic schemas, plus `src/types/auth.ts` (legit frontend-only).
- Shared scaffolding (`ListPageLayout`, `PageHeader`, `FormPanel`, `ErrorBanner`) is well adopted; debt concentrates in HTTP layers, auth services, a few god pages, and unadopted UI primitives.
- Hygiene is good: **0 real `any` usages, 0 `console.log`** (22 console.error/warn).

**Test safety net:** only 1 Playwright spec (`e2e/admin-users.spec.ts`), no unit tests — refactors are guarded mainly by `tsc`/`next build`. **Before TASK-401/403, add two or three Playwright smoke flows (login/refresh/logout, one list page, one mutation)** since tsc cannot catch behavioral regressions in the 401/refresh/consent paths.

---

## TASK-401: Consolidate the four HTTP layers into one transport

- **Category:** data-fetching — **Priority: P1** — **Effort: M** — **SECURITY-SENSITIVE**
- **Files:** `src/api/client.ts` (271 lines; response handling 66–96, 401-refresh 213–225, consent 69), `src/utils/apiClient.ts` (138 lines; 401-refresh 102–110, consent 71–76/105/112), `src/utils/api.ts` (36 lines; duplicate response handling 13–22), `src/utils/tokenRefresh.ts`, `app/page.tsx:23,38` (raw fetch)

**Problem:** Two independent transports (`APIClient.request` and `apiFetch`) each implement credentials, 401→refresh→retry, and the consent-gate 403 interception; `APIClient.handleResponse` and `api.ts handle()` duplicate error-text/204/JSON parsing. Any change to auth/consent semantics must be made twice — the consent interceptor is already asymmetric (`apiFetch` applies it on every response, `APIClient` only on `!response.ok`). Pages import 3 call styles (`api.get` 30 files, `apiFetch` 14 files, generated clients 18 files).

**Steps:**
1. Make `apiFetch` (`src/utils/apiClient.ts`) the single low-level transport: it already owns refresh-coalescing + consent interception and returns raw `Response`.
2. Rewrite `APIClient.request` (`src/api/client.ts:171–228`) to delegate to `apiFetch` for the network call, keeping only its param-serialization (`buildUrl`), body encoding, and typed `handleResponse`. Delete its private `tryRefresh` (104–129) — move the auth-provider-aware refresh into `tokenRefresh.ts` so `apiFetch`'s refresh path also refreshes cached user data.
3. Reimplement `src/utils/api.ts` as a thin alias over the `apiClient` singleton, or deprecate it (see TASK-402); its `handle()` duplicate dies with it.
4. Convert `app/page.tsx:23,38` raw `fetch` to the shared layer (`ExtensionsPublicClient` / `ExtensionsGettingStartedClient` already exist in `src/generated/clients/`).

**Risks / verification:** 401/refresh/consent flows are the most security-sensitive code here; behavior differences (consent interception on 2xx, `unreachable` vs `failed` outcomes, retry-once semantics) must be preserved exactly. Test: expired-cookie flow, offline/VPN-down (must NOT log out), consent-gate redirect, FormData upload, 204 responses.

---

## TASK-402: Adopt generated clients instead of hand-typed endpoint strings

- **Category:** type-safety — **Priority: P1** — **Effort: M**
- **Files:** 30 files import `src/utils/api.ts` and call string endpoints — e.g. `app/organizations/page.tsx:17-20` (`api.get<Array<{ organization_id: string }>>('/course-families')`); 4× `'/git-servers'`, 4× `'/example-repositories'`, 4× `'/course-families'`, 4× `'/consent'`, 3× `'/organizations'`, 3× `'/courses'`. Meanwhile `src/generated/clients/` has 54 clients; `OrganizationsClient`, `GitServersClient`, `CourseFamiliesClient` have **zero** importers.

**Problem:** The codegen pipeline produces typed clients and types for every endpoint, but 30 pages bypass them with hand-typed URL strings and inline generic shapes that silently drift from the API. Two conventions coexist within sibling pages (`app/admin/users/roles/page.tsx` uses 4 generated clients; `app/admin/git-servers/*` uses `api.get` strings).

**Steps:**
1. Standardize on generated clients (they carry param serialization and response types).
2. Migrate `api.get/post` call sites feature-by-feature (organizations, course-families, git-servers, consent, examples first — they map 1:1 to existing clients per `src/generated/clients/client-endpoints.md`).
3. Replace inline response generics with `types/generated` imports.
4. When zero importers remain, delete `src/utils/api.ts` (completes TASK-401).
5. Add an ESLint `no-restricted-imports` rule for `@/src/utils/api` to prevent regression.

**Risks / verification:** Generated method names encode odd casing (`listCoursesCoursesGet`) — mechanical but verbose; check each migrated call's query-param names (snake_case conversion happens inside generated clients). Test: each migrated page loads, filters, mutates.

---

## TASK-403: Retire the dead password-login path and dual auth providers (~350+ unreachable lines)

- **Category:** dead-code — **Priority: P1** — **Effort: M**
- **Files:** `src/services/authService.ts` (278 lines; `login()` at :65), `src/contexts/AuthContext.tsx:96–111` (`login`), `:83–88`, `:123–125`, `:144–149` (authService fallbacks), `src/interfaces/IAuthProvider.ts:62`, `src/config/apiConfig.ts` (registers both providers), `src/types/auth.ts:14-15` (comment: "Local password auth was removed (Keycloak SSO is the only identity provider)")

**Problem:** No UI calls `useAuth().login` — `app/login/page.tsx` is SSO-only (`loginWithSSO` at :22,:32). Yet the app maintains two full auth-service implementations (`authService` 278 + `ssoAuthService` 333 lines) with duplicated `fetchUserViews`, `logout`, `refreshSession`, and a provider-iteration protocol (`IAuthProvider`, `apiConfig`, `APIClient.setAuthProviders`) whose second provider can never be authenticated.

**Steps:**
1. Delete `login` from `AuthContextType` and its implementation (`AuthContext.tsx:19,96–111`).
2. Delete `src/services/authService.ts`; first compare `fetchUserInfo`/`fetchUserViews` against ssoAuthService's and move anything unique (none expected).
3. Collapse `IAuthProvider` to what `APIClient` actually needs (`isAuthenticated`, `refreshSession`, `clearSession`) or drop the interface and depend on `ssoAuthService` directly; simplify `apiConfig.ts` to a single setter.
4. Remove the `authService` branches in `AuthContext` (`initAuth` fallback :82–88, `logout` :123–125, `refreshSession` :144–149) and `authInstances.ts`.

**Risks / verification:** Confirm the backend truly has no `/auth/login` flow in use (SSO-only per TU Graz Keycloak setup). Test: full login → refresh (15-min interval, `AuthContext.tsx:185–201`) → logout cycle; Firefox session-restore case documented at `AuthContext.tsx:57–61`.

---

## TASK-404: Split the 641-line members/add god page into three flow components

- **Category:** god-component — **Priority: P2** — **Effort: M**
- **Files:** `app/courses/[id]/management/members/add/page.tsx` (641 lines, 24 `useState`, three complete flows: user-list tab :52–153/342–472, email tab :155–199/474–532, file-import tab :201–293/534–636)

**Problem:** Three mutually exclusive workflows (pick users, invite by email, parse+import file) in one component; each has its own state cluster, submit handler, and table markup. State names must be suffixed to disambiguate (`rowRole` vs `rowRoleFile`, `rowError` vs `fileError`) — a classic signal the component should be three.

**Steps:**
1. Create co-located components (`app/courses/[id]/management/members/add/` or `src/components/course-members/`): `AddFromUserList.tsx`, `AddByEmail.tsx`, `ImportFromFile.tsx`, each receiving `{ courseId, roleOptions, defaultRole, groups }` as props.
2. Keep the page as the shell: permission guard (:295–303), tab state, breadcrumbs, and the shared `useResource` calls for course/groups (:71–114); pass results down.
3. Extract the repeated role/group `<select>` cells (:396–422 vs :585–604) into small `RoleSelect`/`GroupSelect` components.
4. Move `fileToBase64` (:212–220) to `src/utils/`.

**Risks / verification:** Pure extraction — keep `defaultRole`/`roleOptions` derived once in the shell (they depend on `usePermissions` ceiling logic :42–48). Test: add-from-list incl. student-needs-group validation (:124–132), email import success/failure, file parse → selective import.

---

## TASK-405: Decompose Sidebar.tsx (nav config + icons + data fetching + rendering)

- **Category:** god-component — **Priority: P2** — **Effort: S**
- **Files:** `src/components/Sidebar.tsx` (540 lines): static nav config :33–158, inline SVG icon map :170–218, course-views fetch `useEffect` :243–269, UUID-course-detection :236–240, rendering :279+

**Steps:**
1. Extract `src/config/navigation.ts`: `coursesNavigation`, `workspacesNavigation`, `managementNavigation`, `adminNavigation`, `userMgmtNavigation`, `getViewNavigation`, plus `NavItem`/`SubItem` types.
2. Extract `src/components/icons.tsx` (the `icons` record :170–218); TopBar/others can reuse.
3. Extract a `useCourseViews(courseId)` hook into `src/hooks/` (wrapping :243–269 incl. the UUID guard).
4. Sidebar keeps only expansion state + rendering (`pathMatches`, `renderNavItems`).

**Risks / verification:** Low — mechanical. Test: active-item highlighting (most-specific-match logic :287–295 was a recent bug fix, commit 586be12c), course-context nav appearing only for UUID routes.

---

## TASK-406: Finish the useResource migration (~20 hand-rolled fetch machines)

- **Category:** data-fetching — **Priority: P2** — **Effort: M**
- **Files:** `src/hooks/useResource.ts` (the intended standard per its own docstring); still hand-rolled: `app/courses/[id]/lecturer/assignments/page.tsx:43–101` (manual `cancelled` flag + separate `reload`, duplicating sort+fetch at :58–72 and :90–101), `app/courses/[id]/student/assignments/page.tsx:29–60` (no cancellation), plus ~22 more pages matching `useState(true)` loading booleans (46 `setLoading/setIsLoading` call sites in app/).

**Steps:**
1. Migrate the remaining `useEffect`-fetch pages to `useResource` (fetcher returning a composite object; use the exposed `reload` instead of bespoke reload functions).
2. For polling pages (`app/workspaces/admin/fleet/page.tsx:83–86`), add an optional `refetchInterval` to `useResource` rather than leaving them hand-rolled.
3. Delete the per-page `cancelled` flags and `setLoading` clusters as each page migrates.
4. Do TASK-410 (loading/error presentation) in the same sweep — same files.

**Risks / verification:** `useResource` deps array feeds `useCallback` directly — verify each migrated page's deps to avoid refetch loops. Test: navigate away mid-load (no state-update warnings), reload after mutation still refreshes.

---

## TASK-407: Extract shared ltree tree-building (3 divergent implementations)

- **Category:** duplication — **Priority: P2** — **Effort: S**
- **Files:** `app/courses/[id]/student/assignments/page.tsx:63–121` (`buildTree`) + :135–262 (`renderTree`, recursive expand/collapse), `src/components/progress/ContentTree.tsx:15–40` (second `buildTree` over the same ltree paths), `app/courses/[id]/lecturer/assignments/page.tsx:36–37` (`depthOf`/`lastSegment` flat-indent variant)

**Problem:** Three independent path→tree conversions for the backend `path` (ltree) field, each with its own sorting rules (position-then-path vs path-then-position — **they genuinely disagree**, possibly a latent inconsistency) and its own expand/collapse state.

**Steps:**
1. Create `src/utils/ltree.ts`: `depthOf`, `lastSegment`, `parentPath`, and a generic `buildTree<T extends { path: string; position?: number }>(items): TreeNode<T>[]` with one documented sort order.
2. Rebase `ContentTree.tsx` and the student assignments page on it; the lecturer page keeps flat rendering but uses `depthOf`/`lastSegment` from the util.
3. Optionally extract a generic `TreeList` component (expand/collapse + indent + per-node render prop) consumed by both tree UIs.

**Risks / verification:** Sort-order unification changes visible ordering on one page — confirm intended semantics with the backend (position orders siblings; path orders parents-before-children). Test: nested unit/assignment courses render identically before/after.

---

## TASK-408: Adopt (or delete) the UI primitives — Button, Notification, table styles

- **Category:** consistency — **Priority: P2** — **Effort: M**
- **Files:** `src/components/Button.tsx` (62 lines, imported ONLY by `ConfirmDialog.tsx:4` and `ConfirmDeleteDialog.tsx:5`); 23 copies of the raw primary-button class string (`bg-blue-600 rounded-lg hover:bg-blue-700`) across app/; 40 copies of the table-header class (`uppercase tracking-wider`) in 10 files; `inputCls` exported from `src/components/FormPanel.tsx:9` (a style token living inside a layout component, imported by 22 files); `NotificationContext` + `Notification.tsx` mounted in `app/layout.tsx:33` but `useNotify` has **0 consumers** — pages hand-roll inline success banners instead (e.g. members/add :488–490, lecturer/assignments `releaseMsg`).

**Steps:**
1. Create `src/components/ui/`; move `Button` there; add `Table`/`Th`/`Td` wrappers encoding the repeated thead/td classes; relocate `inputCls` (as an `Input` component or exported token) out of FormPanel.
2. Sweep the 23 raw primary/secondary button sites and 10 table files onto the primitives (start with workspaces + admin areas — densest tables). Button variants must cover the disabled/loading label patterns pages currently inline (`{saving ? 'Adding…' : 'Add'}`).
3. Decide on `useNotify`: either adopt it for the ~7 inline success-message states (`setImportMsg`, `setReleaseMsg`, …) or delete the provider + component to stop carrying an unused context.

**Risks / verification:** Purely visual; screenshot-compare key pages.

---

## TASK-409: Deduplicate workspace tables across admin pages

- **Category:** duplication — **Priority: P2** — **Effort: S**
- **Files:** `src/components/workspaces/WorkspaceTable.tsx` (143 lines, used only by `app/workspaces/page.tsx:225`); hand-rolled equivalents at `app/workspaces/admin/page.tsx:245–342` and `app/workspaces/admin/[userId]/page.tsx:210–280` (both re-implement thead/rows/status-badge layout).

**Steps:**
1. Extend `WorkspaceTable` with `columns`/`renderActions` props (or an `admin` variant) covering the extra owner column and admin actions used at `admin/page.tsx:245+`.
2. Replace both hand-rolled tables; keep page-specific action buttons as render props.

**Risks / verification:** Admin actions (start/stop/delete/rollout) are wired per-row — verify each action still receives the right workspace object. Test: admin list, per-user list, actions on a running and a stopped workspace.

---

## TASK-410: Unify loading/error presentation on list pages

- **Category:** consistency — **Priority: P3** — **Effort: S**
- **Files:** `ListLoading` from `src/components/ListPageLayout.tsx` (used by well-factored pages, e.g. `app/organizations/page.tsx:49`), vs `animate-pulse` skeleton with early full-layout return (`app/courses/[id]/student/assignments/page.tsx:266–287`), vs inline "Loading users…" text (`members/add/page.tsx:371`); errors mostly `ErrorBanner` (74 uses, good) but some pages early-return the entire layout for an error, losing header/breadcrumbs.

**Steps:**
1. Standardize on `ListLoading` + inline `ErrorBanner` inside the persistent `ListPageLayout`/`PageHeader` shell (the pattern the newest pages already use).
2. Convert the early-return pages (grep `if (loading) { return (<AuthenticatedLayout>`) during the TASK-406 useResource migration — same files, do together.

**Risks / verification:** Minimal; visual diff on loading and simulated-error states.

---

## TASK-411: Delete dead components; replace redirect-stub pages with config redirects

- **Category:** dead-code — **Priority: P3** — **Effort: S**
- **Files (0 importers verified):** `src/components/Spinner.tsx` (29), `src/components/progress/ContentTypeChart.tsx` (66), `src/components/progress/ProgressDistributionChart.tsx` (41). Near-dead: `app/courses/[id]/tutor/grading/page.tsx` and `.../tutor/submissions/page.tsx` are "Coming Soon" `NotFound` shells the Sidebar deliberately doesn't link (`Sidebar.tsx:130–132,143–145`); 7+ top-level redirect stubs (`app/student/page.tsx`, `app/lecturer/page.tsx`, `app/tutor/page.tsx`, `app/assignments/page.tsx`, `app/student/courses`, `app/student/assignments`, `app/lecturer/courses`, `app/tutor/students`) — each a ~21-line client component doing `router.replace('/courses')`.

**Steps:**
1. Delete the three unused components (grep-verified zero imports).
2. Replace the redirect stub pages with `redirects()` entries in `next.config.ts` (permanent: false), deleting the page files and directories.
3. Either delete the two tutor "Coming Soon" pages (404 is equivalent) or keep one canonical placeholder — record the decision where the Sidebar comment already points.

**Risks / verification:** External bookmarks to `/student/*` etc. keep working via config redirects; grep `tutor/grading|tutor/submissions` for links before deleting.

---

## TASK-412: Stop hand-mirroring backend schemas in `src/types/workspaces.ts`

- **Category:** type-safety — **Priority: P3** — **Effort: M**
- **Files:** `src/types/workspaces.ts` (178 lines; header: "Mirrors the Python Pydantic schemas from computor-backend/.../coder/schemas.py"), consumed by 9 files; `src/generated/types/roles.ts:70–89` already defines `WorkspaceRoleAssign`, `WorkspaceProvision*`, and `WorkspaceTemplate = "python-workspace" | "matlab-workspace"` — duplicating the hand-written `WorkspaceTemplate` enum at `workspaces.ts:12–15`. Similarly hand-written clients imitating the generated style: `src/clients/CoderClient.ts`, `WorkspaceRolesClient.ts`, `MaintenanceClient.ts`, `OnboardingClient.ts`.

**Steps:**
1. Add the coder/maintenance/onboarding endpoints to the client/type generation pipeline (a generated `WorkspacesClient.ts` already exists — check its coverage first; it may already subsume parts of `CoderClient`).
2. Where generation isn't feasible yet, re-export the generated `WorkspaceTemplate`/`WorkspaceRoleAssign` from `types/workspaces.ts` instead of redefining.
3. Migrate the 9 importers; delete duplicated definitions.

**Risks / verification:** The hand-written enum is used as a value (`WorkspaceTemplate.PYTHON`) while the generated one is a type-only union — call sites need literal strings after migration. Test: provision flow, fleet rollout, role assignment.

---

## TASK-413: Normalize the import-alias schemes

- **Category:** consistency — **Priority: P3** — **Effort: S**
- **Files:** `tsconfig.json` paths (`@/*`, `api/client`, `types/generated`); usage: `@/src/...` 445 imports, bare `types/generated` 86, bare `api/client` 58, `@/src/generated/types` 16, relative `../` 32.

**Steps:**
1. Keep `@/*`. The `api/client` and `types/generated` aliases exist because generated code emits them — if the generator is touchable, switch its emit to `@/src/...`; otherwise keep those two aliases for generated code only and forbid them in hand-written files via `no-restricted-imports`.
2. Codemod hand-written files to `@/src/...` (eslint `import/no-relative-parent-imports` or a one-off sed sweep).

**Risks / verification:** None at runtime (compile-time aliasing); `tsc --noEmit` + `next build` verifies completely.
