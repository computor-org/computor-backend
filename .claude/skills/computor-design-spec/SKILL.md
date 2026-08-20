---
name: computor-design-spec
description: The shared Computor design language — spacing/radius/type ladders, semantic tones, and component vocabulary — with its two bindings (computor-web Tailwind classes, VS Code extension CSS variables). Load before styling anything in computor-web or the extension's webview-ui, before adding a component, and before reviewing a diff for visual consistency.
---

> **Lives in `computor-fullstack/.claude/` but spans two repos.** All Computor
> agents and skills are kept here — the monorepo is the development entry point —
> so this one is loaded even when the change lands in
> `../computor-vsc-extension`. Paths below are written relative to whichever repo
> root the command belongs to; check which one before running it.

# Computor design language

Two surfaces render Computor: the **web app** (`computor-web`, Next.js + Tailwind 4)
and the **extension webviews** (`computor-vsc-extension/webview-ui`, plain CSS).

They cannot share a palette. A webview must follow the user's VS Code theme or it
looks broken in half of them, while the web app owns its own colors. So this spec
defines **one design language with two bindings**: the ladders, the semantic role
names and the component vocabulary are identical; only the values each role
resolves to differ.

When you change one binding, check whether the other needs the same change. When
you need a token that does not exist here, add it *here first*, then to both
bindings.

---

## 1. Ladders (identical on both surfaces)

**Spacing** — 4px base. Never invent an off-ladder value; if a design "needs"
14px, it needs 12px or 16px.

| Step | Value | Web | Extension |
|---|---|---|---|
| 1 | 4px | `p-1` `gap-1` | `var(--sp-1)` |
| 2 | 8px | `p-2` | `var(--sp-2)` |
| 3 | 12px | `p-3` | `var(--sp-3)` |
| 4 | 16px | `p-4` | `var(--sp-4)` |
| 5 | 20px | `p-5` | `var(--sp-5)` |
| 6 | 24px | `p-6` | `var(--sp-6)` |
| 8 | 32px | `p-8` | `var(--sp-8)` |

**Radius** — the one ladder whose *value* is per-surface. The role names are
shared; the panel radius resolves to **8px on the web and 6px in the extension**.
Each surface sits in a different frame: the web app owns its own chrome, while a
webview is embedded in the editor's 6px geometry and looks pasted-on at anything
rounder.

| Role | Web | Extension |
|---|---|---|
| tight (chips, code spans) | `rounded-sm` (2px) | `var(--radius-sm)` (2px) |
| default (buttons, inputs, notices) | `rounded` (4px) | `var(--radius)` (4px) |
| panel (cards, sections, modals) | `rounded-lg` (8px) | `var(--radius-lg)` (6px) |
| pill (badges, toggles) | `rounded-full` | `var(--radius-pill)` |

> These four rungs are the whole ladder. `rounded-xl`, `rounded-2xl` and a bare
> `rounded-md` on the web are off it — correct them when you are already editing
> the file, not in a sweep of their own.

**Type** — the web has a fixed base; the extension inherits the editor's.

| Role | Web | Extension |
|---|---|---|
| body | `text-sm` (14px) | `var(--font-size)` (editor size, 13px default) |
| secondary / meta | `text-xs` (12px) | `var(--font-size-sm)` (12px) |
| micro (table headers, badge.xs) | `text-[11px]` | `var(--font-size-xs)` (11px) |
| page title | `text-3xl font-bold` | `.header h1` (22px) |
| section title | `text-lg font-semibold` | `.section h2` (16px) |

---

## 2. Semantic tones (identical names, different bindings)

**Always name the meaning, never the color.** `tone="error"`, not `color="red"`.
This is the single most important rule in this spec: it is what lets the same
component vocabulary render correctly against a fixed palette on one surface and
an arbitrary user theme on the other.

| Tone | Means | Web binding | Extension binding |
|---|---|---|---|
| `success` | passed, active, healthy | `bg-green-100 text-green-800` | `--c-success` on `--c-success-bg` |
| `warning` | pending, degraded, needs attention | `bg-yellow-100 text-yellow-800` | `--c-warning` on `--c-warning-bg` |
| `error` | failed, denied, destructive | `bg-red-100 text-red-800` | `--c-error` on `--c-error-bg` |
| `info` | informational, a role tag, a link | `bg-blue-100 text-blue-800` | `--c-info` on `--c-info-bg` |
| `muted` | neutral, archived, not-applicable | `bg-gray-100 text-gray-700` | `--c-muted-bg` on `--c-fg-muted` |

Foreground/surface roles:

| Role | Web | Extension |
|---|---|---|
| primary text | `text-gray-900` | `var(--c-fg)` |
| secondary text | `text-gray-500` | `var(--c-fg-muted)` |
| page background | `bg-gray-50` | `var(--c-bg)` |
| panel background | `bg-white` | `var(--c-bg)` |
| border | `border-gray-200` | `var(--c-border)` |
| link | `text-blue-600` | `var(--c-link)` |
| focus ring | `focus:ring-2 focus:ring-blue-500` | `outline 1px var(--c-focus)` |

The web bindings are the **only** place those literal Tailwind palette classes are
allowed — inside the shared component layer (`src/components/**`). A page in
`app/**` that writes `text-gray-500` directly has bypassed the system.

---

## 3. Component vocabulary

Same concepts, same variant names, on both surfaces.

| Concept | Web | Extension |
|---|---|---|
| Button | `<Button variant size>` | `.btn` + `.btn.secondary` / `.danger` / `.ghost` / `.sm` / `.xs` |
| Link-as-button | `<ButtonLink href>` | `<a class="btn">` |
| Status chip | `<Badge tone pill>` | `.badge` + `.badge-success` / `-warning` / `-error` / `-info` / `-muted` |
| Inline message | `<ErrorBanner>` | `.notice` + `.notice.error` / `.success` / `.warning` / `.info` |
| Card / block | (panel classes) | `.section` (+ `.section-description`) |
| Page shell | `ListPageLayout` | `.page-root` (+ `.page-root.wide`) |
| Page header | `<PageHeader breadcrumbs title …>` | `.header` |
| Form block | `<FormPanel>` | `.form-field` / `.form-grid` / `.form-actions` |
| Table | `<Table>` | `.table` |
| Tabs | `<Tabs>` | `.tabs` + `.tab.active` + `.tab-panel.active` |
| Empty state | `<EmptyState>` | `.empty-state` |
| Spinner | `<Spinner>` | `.spinner` |
| Progress | `<ProgressTrack>` | `.progress-track` + `.progress-fill` |
| Modal | `<Modal>` / `<ConfirmDeleteDialog>` | — (no webview equivalent; use a `.section`) |

**Button variants** — `primary` (default, filled), `secondary` (outlined),
`danger` (filled red / theme error), `dangerGhost` (red text, no fill — for a
destructive action repeated in every table row), `ghost` (muted text, no fill).

> The extension has no `dangerGhost`. Add `.btn.danger-ghost` to `base.css` when a
> webview first needs it; do not hand-roll it in a view stylesheet.

**Sizes** — `xs`, `sm`, `md` (default). Same three on both.

---

## 4. Hard rules

**Web (`computor-web`)**

1. Palette utilities (`text-gray-*`, `bg-blue-*`, `border-red-*`, …) appear **only**
   in `src/components/**`. In `app/**`, use the component or add one.
2. No raw `<button>` in `app/**` — use `Button` / `ButtonLink`.
3. Page headers go through `PageHeader`; status chips through `Badge`; inline
   errors through `ErrorBanner`; dialogs through `Modal` / `ConfirmDeleteDialog`.
4. `Badge` takes a **tone**, not a color name.
5. The app is light-only today (`color-scheme: light`, zero `dark:` variants).
   Do not add a one-off `dark:` variant — it produces a half-dark page. Dark mode
   becomes possible only once rule 1 holds; see §6.
6. Custom CSS goes in `app/globals.css` as an `@utility`, with a comment saying
   why a utility class could not do it. That file's existing comments are the
   standard to match.

**Extension (`webview-ui`)**

1. Colors come from `--vscode-*` via the `--c-*` tokens. **No hex or `rgb()`
   outside `shared/base.css`** — a hardcoded color is invisible in the default
   dark theme and unreadable in a light or high-contrast one.
2. Spacing uses `--sp-*`, radii use `--radius-*`. No raw `px` for either.
3. Per-view stylesheets add **layout only**. They never redefine a token or
   restyle a primitive; if two views need the same thing, it belongs in `base.css`.
4. Class names are flat kebab-case; state is a chained class (`.btn.danger`,
   `.tab.active`).
5. After touching webview assets run `npm run check:assets` — `readAsset()`
   swallows a bad path silently and the view renders unstyled with no error.

---

## 5. Known drift (accurate as of 2026-08-10)

Fix opportunistically — when you are already editing the file. Do not open a
sweeping reformat PR.

Both checkers below report the current numbers with `--all`; these were
re-measured on 2026-08-20.

**Web** (`node computor-web/scripts/check-styling.mjs --all`, 74 files in `app/`)
- **1,155** palette-utility occurrences in `app/**` that should be components
  (a further 666 sit legitimately inside `src/components/**`).
- **77** raw `<button>` in `app/**`; only 9 files import `Button`.
- `PageHeader` reaches 40 of 70 pages; a header scaffold (`PageHeader` **or**
  `FormPanel`) reaches 56 of 70. Create/edit is the healthy half — 16 of 18 of
  those routes already go through `FormPanel`.
- `EmptyState` is used on 4 pages against 15 hand-rolled dashed-border empties.
- Three separate ltree tree renderers draw the same course content hierarchy at
  three different indents.
- `Badge` still takes literal color names (`green`, `purple`) — migrate its API to
  tones, keeping the color names as deprecated aliases until callers are moved.
- `src/components/ui/tokens.ts` holds exactly one string (`inputCls`); the rest of
  the shared class strings are still inlined in components.

**Extension** (`node scripts/check-webview-styling.js --all`, 24 stylesheets)
- **24** hardcoded hex/`rgba()` declarations across 6 non-base stylesheets
  (`shared/markdown-preview.css`, `shared/chat-shared.css`, `courses/charts.css`,
  `figures/figures.css`, `messaging/messages.css`, `images/image-preview.css`).
- **165** raw `px` spacing/radius declarations bypassing `--sp-*` / `--radius-*`.
- **8** base primitives redefined in view stylesheets — `.empty-state` in four
  separate files, plus `.form-grid`, `.chip`, `.status-badge`, `.header`. Each
  is a fork of something `base.css` already provides.
- `.form-field` is declared twice in `base.css`, the first with an off-ladder
  `margin-bottom: 14px`.
- Duplicate spellings `.btn.secondary` / `.btn-secondary` (and `.sm`/`-sm`,
  `.xs`/`-xs`) — the chained form is canonical; the hyphenated one is legacy.

## 6. Dark mode on the web (not yet — the prerequisite)

The web app declares `color-scheme: light` and has zero `dark:` variants. Adding
them page by page is what produces a half-broken dark theme, so it is forbidden
by §4 rule 5.

The order that works: get rule 1 to hold (palette only in `src/components/**`),
promote the §2 bindings into CSS custom properties in `globals.css`, point the
components at those properties, and only then add one `@media (prefers-color-scheme: dark)`
block that redefines them. One change, whole app, no per-page audit.

## Checks

```bash
# web — palette utilities and raw <button> outside the component layer
node computor-web/scripts/check-styling.mjs

# extension — hardcoded colors and raw px outside base.css
node scripts/check-webview-styling.js     # from the extension repo root
npm run check:assets                      # every referenced asset exists
```
