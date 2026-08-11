---
name: computor-web
description: The Computor web frontend (computor-web) — Next.js 16 App Router, React 19, Tailwind 4, TypeScript. Use when adding or changing a page, route, shared component, data-fetching hook or client-side auth behaviour in the web UI.
---

# Computor web UI

Next.js 16 (App Router, **all pages are client components**), React 19,
Tailwind 4, TypeScript. Lives at `computor-fullstack/computor-web`.

**Read first:** `computor-web/README.md` — it documents the layout, conventions,
auth model and test commands. Load the **`computor-design-spec`** skill before
writing any markup.

## Non-negotiables

- **yarn, never npm.** Yarn v1. `yarn dev` (:3000), `yarn lint`, `yarn build`,
  `yarn test:e2e`.
- **Never hand-edit `src/generated/`.** Regenerate from the monorepo root with
  `bash generate.sh`. Import path alias is `@/src/...`.
- Data fetching goes through `useResource`; mutations report through `useNotify()`
  toasts. Role gating goes through `usePermissions()` — and the backend enforces
  every action regardless, so UI gating is affordance, not security.
- Binary downloads must not use the generated clients — they corrupt zips. Use
  `apiFetch` + `res.blob()`, and remember `Content-Disposition` needs to be in the
  backend's CORS `expose_headers`.

## Page conventions

Entity routes: `/{entity}`, `/{entity}/create`, `/{entity}/{id}`,
`/{entity}/{id}/edit`. Create and edit are **`FormPanel` pages, never modals**.
Every page gets `PageHeader` with breadcrumbs. Course navigation uses sidebar
tabs — no quick-action grids.

Copy the shape of an existing well-formed route rather than inventing one;
`app/admin/services/` and `app/admin/git-servers/` are the cleanest examples of
the full list/create/detail/edit set.

Component vocabulary — use these, do not hand-roll:
`PageHeader`, `Breadcrumbs`, `ListPageLayout`, `FormPanel`, `Modal`,
`ConfirmDialog`, `ConfirmDeleteDialog` (type-to-confirm, for destructive deletes),
`ErrorBanner`, `EmptyState`, `Badge`, `Avatar`, `Notification`, and from
`src/components/ui/`: `Button`/`ButtonLink`, `Table`, `Tabs`, `Toggle`,
`Spinner`, `ProgressTrack`.

## Styling

The full rules are in the `computor-design-spec` skill. The two that matter most
here:

- **Tailwind palette utilities (`text-gray-500`, `bg-blue-600`, …) belong only in
  `src/components/**`.** A page in `app/**` that styles with raw palette classes
  has bypassed the system — use the component, or add one.
- **No raw `<button>` in `app/**`** — use `Button` / `ButtonLink`.

Run `node computor-web/scripts/check-styling.mjs` before finishing.

The app is light-only (`color-scheme: light`, zero `dark:` variants). Do not add
a one-off `dark:` — it yields a half-dark page. The spec explains the ordering
that makes dark mode possible.

## Auth in the browser

Keycloak SSO brokered by the backend; tokens in HttpOnly cookies; only
non-sensitive user data in `sessionStorage` (`src/services/authStorage.ts`).
Token refresh on 401 goes through the single-flight guard in
`src/utils/tokenRefresh.ts` — do not add a second refresh path.

## Verifying

`yarn test:e2e` (Playwright, network-mocked — no backend or DB needed; first run
`npx playwright install chromium`). For a real end-to-end check against the dev
stack, use the `verify` skill. Note the dev server holds `.next/dev/lock`, so
Playwright cannot start its own while `web.sh` is running — reuse it with
`E2E_PORT=3000 npx playwright test …`.
