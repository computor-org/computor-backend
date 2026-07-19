/*
 * Patches code-server's webview host (VS Code's pre/index.html) so a failed
 * or stuck service-worker handshake no longer aborts webview rendering
 * (computor-org/issues#274).
 *
 * Upstream behavior: before writing a webview's HTML into its iframe, the
 * host awaits `workerReady` (service-worker registration). When registration
 * fails — Safari private windows, Lockdown Mode, blocked site data — or never
 * settles, every webview stays a silent blank panel, even ones that inline
 * all their assets and never touch the service worker (all computor webviews
 * since computor-vscode#267). Chrome is unaffected, which is why this only
 * surfaced on Safari.
 *
 * The patch caps the wait at 8s and drops the abort on failure, so content is
 * always written; only asWebviewUri resource loads degrade in browsers whose
 * service worker is actually broken — strictly better than a blank panel.
 *
 * The host's inline <script> is allowlisted by a sha256 hash in its own CSP
 * meta tag, so the hash is recomputed and swapped alongside the edit. Every
 * step is verified; any mismatch (e.g. a code-server upgrade changed the
 * file) fails the image build loudly instead of shipping a broken patch.
 *
 * Applied once in docker/code-server-base/Dockerfile (computor-code-server),
 * the shared base every code-server workspace template builds FROM. Run with
 * code-server's bundled node:
 *   /usr/lib/code-server/lib/node patch-webview-host.js <path-to-pre/index.html>
 */
'use strict';

const fs = require('fs');
const crypto = require('crypto');

const file = process.argv[2];
if (!file) {
  console.error('usage: node patch-webview-host.js <path-to-pre/index.html>');
  process.exit(1);
}

const fail = (msg) => {
  console.error(`patch-webview-host: ${msg} (${file})`);
  console.error('Refusing to continue — check whether a code-server update changed the webview host.');
  process.exit(1);
};

let html = fs.readFileSync(file, 'utf8');

const scriptMatch = html.match(/<script async type="module">([\s\S]*?)<\/script>/);
if (!scriptMatch) fail('inline module script not found');
const script = scriptMatch[1];

const hashOf = (s) =>
  'sha256-' + crypto.createHash('sha256').update(s, 'utf8').digest('base64');

const declaredMatch = html.match(/script-src '(sha256-[A-Za-z0-9+/=]+)'/);
if (!declaredMatch) fail('CSP script-src hash not found');
if (declaredMatch[1] !== hashOf(script)) {
  fail(`declared CSP hash ${declaredMatch[1]} does not match the current inline script`);
}

const original =
  '\t\t\t\ttry {\n' +
  '\t\t\t\t\tawait workerReady;\n' +
  "\t\t\t\t\tperfMark('content/workerReady');\n" +
  '\t\t\t\t} catch (e) {\n' +
  '\t\t\t\t\tconsole.error(`Webview fatal error: ${e}`);\n' +
  "\t\t\t\t\thostMessaging.postMessage('fatal-error', { message: e + '' });\n" +
  '\t\t\t\t\treturn;\n' +
  '\t\t\t\t}';

const replacement =
  '\t\t\t\ttry {\n' +
  '\t\t\t\t\t// computor #274: cap the wait so a stuck service worker cannot blank the webview forever\n' +
  '\t\t\t\t\tawait Promise.race([workerReady, new Promise(r => setTimeout(r, 8000))]);\n' +
  "\t\t\t\t\tperfMark('content/workerReady');\n" +
  '\t\t\t\t} catch (e) {\n' +
  '\t\t\t\t\tconsole.error(`Webview fatal error: ${e}`);\n' +
  "\t\t\t\t\thostMessaging.postMessage('fatal-error', { message: e + '' });\n" +
  '\t\t\t\t\t// computor #274: no return — render the content anyway. Webviews that inline\n' +
  '\t\t\t\t\t// their assets work without the service worker; a blank panel helps no one.\n' +
  '\t\t\t\t}';

if (script.includes(replacement)) {
  console.log('patch-webview-host: already patched, nothing to do');
  process.exit(0);
}
const occurrences = script.split(original).length - 1;
if (occurrences !== 1) fail(`expected exactly 1 workerReady abort block, found ${occurrences}`);

const patchedScript = script.replace(original, () => replacement);
html = html
  .replace(script, () => patchedScript)
  .replace(declaredMatch[1], () => hashOf(patchedScript));

fs.writeFileSync(file, html);
console.log(`patch-webview-host: patched ${file}`);
console.log(`patch-webview-host: CSP hash ${declaredMatch[1]} -> ${hashOf(patchedScript)}`);
