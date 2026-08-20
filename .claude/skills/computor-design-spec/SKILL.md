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

### 2a. The web's tokens

On the web those bindings are **CSS custom properties in `app/globals.css`**,
registered with `@theme inline` so Tailwind emits a utility for each. Use the
utility; never the palette.

| Role | Utility | Was |
|---|---|---|
| primary text | `text-fg` | `text-gray-900` |
| running text | `text-body` | `text-gray-700` |
| secondary / label | `text-muted` | `text-gray-500/600` |
| hint / timestamp | `text-subtle` | `text-gray-400` |
| card, panel | `bg-surface` | `bg-white` |
| page behind them | `bg-canvas` | `bg-gray-50` |
| well inside a card | `bg-sunken` | `bg-gray-100` |
| panel / table border | `border-rule` | `border-gray-200` |
| row separator | `border-rule-soft` / `divide-rule-soft` | `border-gray-100` |
| input border | `border-rule-strong` | `border-gray-300` |
| button fill | `bg-accent` / `hover:bg-accent-hover` | `bg-blue-600/700` |
| text on that fill | `text-on-accent` | `text-white` |
| link / accent text | `text-accent-text` | `text-blue-600` |
| tint behind a chip | `bg-accent-wash` | `bg-blue-50` |

The same three registers exist for `danger`, `warn` and `success`
(`bg-*-wash`, `text-*-text`, `border-*-line`, plus `bg-danger` / `bg-success`
fills). `bg-inverse` is a surface that flips against the page.

This is what makes dark mode a single block rather than a per-page audit — see §6.

Literal Tailwind palette classes are allowed **nowhere** in `app/**`, and inside
`src/components/**` only where no token fits.

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
5. **Never write a `dark:` variant.** The app has dark mode and it works through
   the tokens in rule 1 — a per-page `dark:` override is how you get a page that
   is half-dark. If something looks wrong in dark mode, the fix is a token.
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

**Web** (`node computor-web/scripts/check-styling.mjs --all`, 75 files in `app/`)
- **0** palette-utility occurrences in `app/**` — down from 1,155. Colours are
  named by role now (see §2a); the checker will block a regression at commit time.
- **71** raw `<button>` in `app/**`. This is the remaining debt: each one is a
  `Button` with a hand-rolled class string. Concentrated in `settings` (8),
  `admin/users/[id]` (8), `admin/updates` (7), `admin/users/invites` (5).
- A header scaffold (`PageHeader` / `FormPanel` / `DetailPanel`) reaches **59 of
  71** pages. The remaining 12 are correct as they are and should NOT be
  "fixed": four sit outside the app shell (the public landing page, login,
  auth/success, the invite acceptance page), three are redirect stubs, three are
  `ComingSoon` states, one is a thin wrapper whose child owns the header, and one
  (`workspaces/launch`) is deliberately standalone with a comment saying why.
  Count adoption against the 59, not against 71.
- `Badge` takes `tone`; the old `color` names remain as deprecated aliases.
  New code passes `tone`.

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

## 6. Dark mode on the web

Shipped. `app/globals.css` defines the light palette on bare `:root`, then
redefines the same tokens twice: under
`@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }` and
under `:root[data-theme="dark"]`.

Three states, not two — an explicit choice stamps `data-theme` on `<html>`, and
the default "system" setting stamps nothing, so only `prefers-color-scheme`
separates light from dark there. The guards make an explicit choice win in both
directions. `e2e/theme-check.spec.ts` asserts all four combinations.

The preference lives in `localStorage` under `computor-theme` and is applied by a
blocking inline script in `app/layout.tsx` **before first paint** — read it in a
component instead and dark-mode users get a white flash on every document load.
`ThemePicker` (on `/settings`) reads it through `useSyncExternalStore`, because
this repo's lint forbids `setState` inside an effect and the server has no
`localStorage` to render against.

Dark is not an inversion of light: the greys are re-picked so contrast holds, and
the washes are deep tints — a lightened wash on a dark ground reads as a hole in
the page. The accent **fill** stays `#2563eb` in both themes so white button text
keeps 5.17:1; only the accent *text* lightens.

To change a colour in either theme, edit the token. Never add a `dark:` variant.

## Checks

```bash
# web — palette utilities and raw <button> outside the component layer
node computor-web/scripts/check-styling.mjs

# extension — hardcoded colors and raw px outside base.css
node scripts/check-webview-styling.js     # from the extension repo root
npm run check:assets                      # every referenced asset exists
```
