---
name: computor-extension
description: The Computor VS Code extension (computor-vsc-extension) — TypeScript extension host, tree views, commands, webview providers and webview-ui assets. Use when adding or changing a view, command, tree provider or webview, or debugging extension behaviour in the editor.
---

# Computor VS Code extension

TypeScript, webpack-bundled. Repo `computor-vsc-extension` (sibling of
`computor-fullstack`). Student, tutor and lecturer surfaces in one extension.

> You are defined in `computor-fullstack/.claude/` — the monorepo is the
> development entry point — but the code you edit is in the **sibling repo**.
> `cd ../computor-vsc-extension` before running any command below, and commit
> there. If that directory does not exist, say so and stop rather than guessing.

**Read first:** `docs/architecture.md` and `docs/developer-guide.md` in the repo.

## Layout

| Path | Owns |
|---|---|
| `src/extension.ts` | activation, command registration |
| `src/ui/tree/` | tree data providers, split `student/ tutor/ lecturer/ …` |
| `src/ui/webviews/` | one provider per view, all extending `BaseWebviewProvider` |
| `src/ui/webviews/shared/webviewPage.ts` | `renderWebviewPage()` — inlines CSS/JS assets |
| `src/ui/editorLayout.ts` | which editor column a file opens in |
| `webview-ui/` | webview CSS/JS, grouped by feature |
| `src/types/generated/` | generated from backend pydantic — **never hand-edit** |
| `src/http/`, `src/authentication/` | API client, token handling |

Commands: `npm run compile` (type-check + webpack), `npm run watch`,
`npm run type-check`, `npm run lint`, `npm run test:unit`, `npm run check:assets`.

## Rules that exist because something broke

- **Every file open goes through `src/ui/editorLayout.ts` and the
  `computor.openFile` command.** Sources land in column One, auxiliary surfaces
  (figures, previews, images) in column Two. **Never** pass `ViewColumn.Beside`,
  `Active`, or omit the column — those are relative, so the layout drifts as soon
  as focus moves, and `Beside` computed while a figure has focus opens a third
  group (issue #286). Images count as figures; a `.md` opened for editing is
  source, a markdown *preview* is auxiliary.
- **After touching webview assets, run `npm run check:assets`.** `readAsset()`
  swallows errors with a bare catch, so a mistyped path emits no error — the view
  just renders unstyled or dead. `webview-ui/` is outside the TypeScript program,
  is not linted and has no test coverage; that script is the only guard.
- **UI state has exactly one store: `UiStateService`** (container, expansion,
  selection). Do not add a second cache. `reveal()` needs `getParent`, so go
  through the `treeRestore.ts` wrapper. Restoring state must never replay side
  effects.
- **Scope a render path to its own node.** A course-tree render that writes the
  *global* selection let a still-expanded old course re-elect its own member on
  switch (issue #287). Anything a render path writes must be keyed by the node it
  rendered.
- The extension is baked into the workspace **image**, not the home volume — a
  home-volume wipe does not update it; a rebuild does. Clone caching by branch
  name once pinned a stale extension forever and still reported success; source
  repos are SHA-pinned for that reason.

## Webviews

One provider per view extending `BaseWebviewProvider`; markup rendered through
`renderWebviewPage()` with `cssFiles`/`scriptFiles` arrays. Paths must be
folder-qualified (`shared/base.css`, not `base.css`) — the flat layout is gone
and `check:assets` enforces it.

Styling is governed by the **`computor-design-spec`** skill; load it before
writing webview CSS. In short: colors come from `--vscode-*` via the `--c-*`
tokens, spacing from `--sp-*`, radii from `--radius-*`; **no hex or `rgb()`
outside `shared/base.css`**; per-view stylesheets add layout only. Verify a new
view against both a dark and a light theme.

KaTeX is vendored (`npm run vendor:katex`, data-URI fonts) because a webview
cannot load remote assets; math is extracted *before* `marked` runs, and all
built-in previews go through the shared `showMarkdownPreview`.

## Generated types

`src/types/generated/` comes from the backend's pydantic models but **nothing
automates the copy** — no codegen path in the monorepo targets this repo. After a
backend DTO change, regenerate this leg explicitly and run `npm run type-check`;
nothing else will tell you it is stale. See the `computor-api-contract` agent.

## Verifying

`npm run compile` must pass — it type-checks before bundling. Then load the
extension host and exercise the actual view; tree and webview bugs here are
almost never visible in unit tests.
