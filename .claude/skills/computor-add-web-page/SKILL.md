---
name: computor-add-web-page
description: Add a page or full entity route set to the Computor web UI (computor-web) following its App Router conventions, component vocabulary and design spec. Use when creating a new route, list/detail/create/edit set, or a new shared web component.
---

# Adding a page to computor-web

Next.js 16 App Router, React 19, Tailwind 4. **All pages are client components**
(`'use client'` at the top). Import alias is `@/src/...`. Package manager is
**yarn**, never npm.

Load the **`computor-design-spec`** skill before writing markup.

## The route set

An entity gets four routes, in this shape:

```
app/<entity>/page.tsx              list
app/<entity>/create/page.tsx       create   — a FormPanel page, never a modal
app/<entity>/[id]/page.tsx         detail
app/<entity>/[id]/edit/page.tsx    edit     — a FormPanel page, never a modal
```

`app/admin/services/` and `app/admin/git-servers/` are the closest things to
reference implementations — copy their structure. (Read them critically: the
services list page still hand-rolls its "New" link and its empty state instead of
using `ButtonLink` and `EmptyState`. Copy the skeleton, not those two spots.)

## The skeleton

```tsx
'use client';

import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollPanel, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import Forbidden from '@/src/components/Forbidden';
import { ButtonLink } from '@/src/components/ui/Button';
import { Table, Thead, Tbody, Tr, Th, Td } from '@/src/components/ui/Table';
import { ThingsClient } from '@/src/generated/clients/ThingsClient';

const thingsClient = new ThingsClient();

export default function ThingsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isSomeRole: canManage } = usePermissions();

  const { data, loading, error } = useResource(
    () => thingsClient.listThings({}),
    [],
    { enabled: canManage },
  );
  const things = data ?? [];

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="… access is required to manage things." />;
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Things' }]}
          title="Things"
          subtitle="One sentence saying what these are and why they exist."
          actions={<ButtonLink href="/things/create">New Thing</ButtonLink>}
        />
        <ErrorBanner>{error}</ErrorBanner>
        {loading ? <ListLoading>Loading…</ListLoading>
          : things.length === 0 ? <EmptyState>No things yet.</EmptyState>
          : <ScrollPanel><Table>{/* … */}</Table></ScrollPanel>}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
```

## Rules

- **Data through `useResource`; mutations report through `useNotify()` toasts.**
- **Role gating through `usePermissions()`** — and remember the backend enforces
  every action anyway. UI gating is affordance, not security.
- **Never hand-edit `src/generated/`.** If the client method you need does not
  exist, the backend needs an `EntityInterface` and a regeneration, not a
  hand-written fetch.
- **Destructive deletes use `ConfirmDeleteDialog`** (type-to-confirm). Simple
  confirmations use `ConfirmDialog`. Both render through `Modal`.
- **Binary downloads bypass the generated clients** — they corrupt zips. Use
  `apiFetch` + `res.blob()`, and check `Content-Disposition` is in the backend's
  CORS `expose_headers`.
- Course navigation is sidebar tabs. No quick-action grids.

## Styling

Palette utilities (`text-gray-500`, `bg-blue-600`, …) belong **only** in
`src/components/**`. If your page needs a styled thing, use the component or add
one. No raw `<button>` — use `Button` / `ButtonLink`. Do not add `dark:`
variants; the app is light-only and a per-page variant produces a half-dark page.

## Before finishing

```bash
node computor-web/scripts/check-styling.mjs
yarn lint
npx tsc --noEmit
yarn test:e2e            # Playwright, network-mocked, no backend needed
```

If `web.sh` is already running, Playwright cannot start its own server
(`.next/dev/lock`) — reuse it: `E2E_PORT=3000 npx playwright test …`.
