---
name: computor-add-webview
description: Add a webview to the Computor VS Code extension — provider, HTML rendering, webview-ui assets, message passing and the asset check. Use when creating a new webview panel or editor in computor-vsc-extension, or restructuring an existing one.
---

# Adding a webview to the Computor extension

Load the **`computor-design-spec`** skill before writing any CSS.

## The pieces

```
src/ui/webviews/ThingWebviewProvider.ts     extends BaseWebviewProvider
webview-ui/<feature>/thing.css              layout only — tokens come from base.css
webview-ui/<feature>/thing.js               view script
```

`BaseWebviewProvider` owns the panel lifecycle: `show(title, data)`, reveal-if-
exists, `handleMessage`, dispose cleanup, and `localResourceRoots` scoped to
`webview-ui/`. Subclass it — do not call `createWebviewPanel` yourself.

Markup is produced by `renderWebviewPage()`
(`src/ui/webviews/shared/webviewPage.ts`) with `cssFiles` / `scriptFiles`
arrays. It **always** prepends `shared/base.css` and `shared/base.js`, so never
list those yourself.

```ts
return renderWebviewPage(webview, {
  title: 'Thing',
  nonce: getNonce(),
  cssFiles: ['courses/thing.css'],      // folder-qualified, always
  scriptFiles: ['courses/thing.js'],
  body: `…`,
});
```

## The silent failure

`readAsset()` swallows errors with a bare catch. A mistyped path produces **no
error at all** — the view renders unstyled or dead, and nothing in the build
catches it: `webview-ui/` is outside the TypeScript program, is not linted and
has no test coverage.

```bash
npm run check:assets
```

Run it after every asset change. It verifies each referenced file exists, that
paths are folder-qualified, and reports orphaned files.

## Styling rules

1. Colors come from `--vscode-*` through the `--c-*` semantic tokens. **No hex or
   `rgb()` outside `shared/base.css`.** A hardcoded color is invisible in one
   theme and unreadable in another.
2. Spacing uses `--sp-*`, radii use `--radius-*`. No raw `px` for either.
3. Your view stylesheet adds **layout only**. Primitives (`.btn`, `.badge`,
   `.notice`, `.section`, `.table`, `.tabs`, `.empty-state`, `.spinner`) already
   exist in `base.css` — use them. If two views need the same new primitive, it
   belongs in `base.css`, not duplicated.
4. Flat kebab-case class names; state is a chained class (`.btn.danger`,
   `.tab.active`).
5. Wrap the view in `.page-root` (or `.page-root.wide`) and use `.section` blocks
   — the column gap owns the spacing, so those sections drop their own margin.

## Messaging

Extension → webview via `panel.webview.postMessage`; webview → extension via
`acquireVsCodeApi().postMessage`, handled in your `handleMessage` override.
Treat every inbound message as untrusted input and switch on a known command set.
A CSP nonce is required for scripts — `getNonce()` provides it; do not inline
event handlers in HTML, they are blocked.

Webviews cannot load remote assets. Anything external must be vendored (KaTeX
already is: `npm run vendor:katex`, data-URI fonts).

## Opening files from a webview

Go through the `computor.openFile` command and `src/ui/editorLayout.ts`. Never
`ViewColumn.Beside`, `Active`, or an omitted column — those are relative and the
layout drifts as focus moves. Sources go to column One, figures/previews/images
to column Two.

## Before finishing

```bash
npm run check:assets
npm run compile          # type-check + webpack
node scripts/check-webview-styling.js
```

Then load the extension host and open the view against **both a dark and a light
theme**. A hardcoded color looks fine in exactly one of them, which is how they
get shipped.
