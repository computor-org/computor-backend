# computor-web

Web frontend for [Computor](https://github.com/computor-org/computor-backend), the educational platform for programming courses. Next.js 16 (App Router, client-side rendering), React 19, Tailwind CSS 4, TypeScript.

## Getting started

```bash
yarn install
yarn dev            # http://localhost:3000
```

The app talks to the Computor FastAPI backend. Configuration:

| Env var | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL. Baked in at build time (`NEXT_PUBLIC_*`), so set it when building the Docker image for production. |
| `NEXT_PUBLIC_ANALYTICS_DEMO` | unset | `1` renders the lecturer analytics against synthetic data with no backend/auth — local UI development only, never set in production. |

See `docker/ENV_VARIABLES.md` for the Docker build details.

## Authentication

Sign-in is Keycloak SSO (brokered by the backend). Tokens live in HttpOnly cookies set by the backend; the frontend stores only non-sensitive user data in `sessionStorage` (see `src/services/authStorage.ts`). All HTTP layers refresh the access token on 401 through a single-flight guard (`src/utils/tokenRefresh.ts`).

Role gating in the UI goes through `usePermissions()` (`src/hooks/usePermissions.ts`), which derives from the backend's `/user/scopes` and `/user/views`. The backend enforces every action regardless.

## Project layout

```
app/                    Routes (App Router; all pages are client components)
src/components/         Shared UI (PageHeader, FormPanel, Modal, ConfirmDialog,
                        Button, Badge, Spinner, EmptyState, ErrorBanner, …)
src/contexts/           AuthContext, NotificationContext (useNotify toasts)
src/hooks/              useResource (data fetching), usePermissions, …
src/api/client.ts       APIClient used by all generated clients
src/generated/          API clients + types generated from the backend
                        (do not edit by hand; regenerate via ../generate.sh)
src/services/           Auth services (SSO + basic fallback)
e2e/                    Playwright tests (network-mocked, no backend needed)
```

Conventions:
- Data fetching on pages goes through `useResource`; mutations report via `useNotify()` toasts.
- Dialogs render through `Modal` (focus trap + dialog semantics). Destructive deletes use `ConfirmDeleteDialog` (type-to-confirm); simple confirmations use `ConfirmDialog`.
- Page headers use `PageHeader`; inline errors use `ErrorBanner`; status chips use `Badge`.

## Testing

```bash
yarn test:e2e       # Playwright; starts its own next dev server on :3100
```

The e2e tests mock the backend at the network layer (`e2e/fixtures.ts`), so they need no running API or database. First run: `npx playwright install chromium`.

## Lint / build

```bash
yarn lint
yarn build
```
