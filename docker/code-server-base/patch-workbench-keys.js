/*
 * Appends a Cmd+Z guard to code-server's workbench entry script
 * (computor-org/issues#313).
 *
 * In Safari, Cmd+Z with nothing to undo falls through to the browser, which
 * treats it as "reopen last closed tab" and yanks the student out of the
 * workspace. That happens whenever focus is on a non-editable surface (the
 * file tree, a panel): VS Code sees the keydown, has nothing bound to do,
 * and does not preventDefault. Chrome and Firefox simply do nothing there.
 *
 * The guard runs at capture time and only calls preventDefault — it never
 * stops propagation, so VS Code's own undo handling is untouched. Editable
 * targets (inputs, textareas, contenteditable — including Monaco's hidden
 * textarea) are exempt because their native undo needs the default.
 *
 * The workbench page carries no CSP meta and loads this file same-origin, so
 * appending needs no hash juggling (unlike patch-webview-host.js). Applied in
 * docker/code-server-base/Dockerfile. Run with code-server's bundled node:
 *   /usr/lib/code-server/lib/node patch-workbench-keys.js <path-to-workbench.js>
 */
'use strict';

const fs = require('fs');

const file = process.argv[2];
if (!file) {
  console.error('usage: node patch-workbench-keys.js <path-to-workbench.js>');
  process.exit(1);
}

const fail = (msg) => {
  console.error(`patch-workbench-keys: ${msg} (${file})`);
  console.error('Refusing to continue — check whether a code-server update moved the workbench entry script.');
  process.exit(1);
};

const MARKER = 'computor-org/issues#313';

let js;
try {
  js = fs.readFileSync(file, 'utf8');
} catch (e) {
  fail(`cannot read: ${e.message}`);
}
if (js.length < 100) fail('file is implausibly small — wrong target?');
if (js.includes(MARKER)) {
  console.log('patch-workbench-keys: already applied, nothing to do');
  process.exit(0);
}

const snippet = `
/* ${MARKER}: keep Safari's Cmd+Z-with-nothing-to-undo from leaving the page.
 * preventDefault only, at capture — VS Code's own handling is untouched, and
 * editable targets keep their native undo. */
(function () {
  try {
    var nav = typeof navigator !== 'undefined' ? navigator : {};
    if (!/Mac|iP(hone|ad|od)/.test(String(nav.platform || nav.userAgent || ''))) { return; }
    var isEditable = function (el) {
      for (; el; el = el.parentElement) {
        if (el.isContentEditable) { return true; }
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') { return true; }
      }
      return false;
    };
    window.addEventListener('keydown', function (e) {
      if (e.metaKey && !e.ctrlKey && !e.altKey && (e.key === 'z' || e.key === 'Z')) {
        if (!isEditable(e.target)) { e.preventDefault(); }
      }
    }, true);
  } catch (e) { /* never break the workbench over a key shim */ }
})();
`;

fs.appendFileSync(file, snippet);

if (!fs.readFileSync(file, 'utf8').includes(MARKER)) {
  fail('append did not stick');
}
console.log('patch-workbench-keys: applied');
