#!/usr/bin/env node
/**
 * Enforces the Computor design spec on computor-web.
 *
 * Three rules. The first two are the same point — the shared component layer is
 * where styling decisions live, and `app/**` is where they get bypassed:
 *
 *   1. Tailwind palette utilities (text-gray-500, bg-blue-600, border-red-200…)
 *      appear only in src/components/**. A page that writes them directly has
 *      forked the palette, which is why the app has ~1,200 such occurrences and
 *      no way to add dark mode.
 *   2. No raw <button> in app/** — use Button / ButtonLink, so focus, disabled
 *      and loading states stay consistent.
 *   3. No `dark:` variants. The app is light-only (globals.css declares
 *      color-scheme: light). Adding them one page at a time yields a half-dark
 *      app; real dark mode needs rule 1 to hold first, then one token swap.
 *
 * Ratchet, not a wall. The existing drift is large, so by default this checks
 * only the files you have actually changed (vs. the merge-base with the release
 * branch, falling back to HEAD). New and edited code comes out clean; the rest
 * is fixed opportunistically. `--all` prints the full inventory without failing,
 * for when you want to see the size of the problem.
 *
 * Usage:
 *   node scripts/check-styling.mjs            # changed files; exits 1 on violations
 *   node scripts/check-styling.mjs --all      # full inventory, always exits 0
 *   node scripts/check-styling.mjs <paths…>   # explicit files
 */

import { execSync } from 'node:child_process';
import { readFileSync, existsSync, statSync } from 'node:fs';
import { readdirSync } from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const WEB_ROOT = path.resolve(new URL('..', import.meta.url).pathname);
const BASE_REF = process.env.COMPUTOR_BASE_REF || 'release/2026.10';

const PALETTE =
  /\b(?:bg|text|border|ring|divide|from|to|via|outline|decoration|placeholder|accent|caret|shadow)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/g;
// \b so it still matches when JSX wraps the attributes onto the next line.
const RAW_BUTTON = /<button\b/g;
const DARK_VARIANT = /\bdark:/g;

/** A line that opts out, with a reason. */
const OPT_OUT = 'design-spec: allow';

function sh(cmd) {
  try {
    return execSync(cmd, { cwd: WEB_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
  } catch {
    return '';
  }
}

function changedFiles() {
  let base = sh(`git merge-base HEAD ${BASE_REF}`).trim();
  if (!base) base = 'HEAD';
  const out = [
    sh(`git diff --name-only --diff-filter=ACM ${base}`),
    sh('git diff --name-only --diff-filter=ACM'),
    sh('git diff --name-only --diff-filter=ACM --cached'),
  ].join('\n');

  const repoRoot = sh('git rev-parse --show-toplevel').trim();
  return [...new Set(out.split('\n').filter(Boolean))]
    .map((p) => (repoRoot ? path.resolve(repoRoot, p) : path.resolve(WEB_ROOT, p)))
    .filter((p) => p.endsWith('.tsx') && existsSync(p));
}

function walk(dir, out = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, out);
    else if (entry.name.endsWith('.tsx')) out.push(full);
  }
  return out;
}

/** Only `app/**` is governed; `src/components/**` is where the palette belongs. */
function isGoverned(file) {
  const rel = path.relative(WEB_ROOT, file);
  return rel.startsWith(`app${path.sep}`) || rel === 'app';
}

function scan(file) {
  const rel = path.relative(WEB_ROOT, file);
  const findings = [];
  const lines = readFileSync(file, 'utf8').split('\n');

  lines.forEach((line, i) => {
    if (line.includes(OPT_OUT)) return;
    const prev = i > 0 ? lines[i - 1] : '';
    if (prev.includes(OPT_OUT)) return;

    for (const m of line.matchAll(PALETTE)) {
      findings.push({ rel, line: i + 1, rule: 'palette', detail: m[0] });
    }
    for (const _ of line.matchAll(RAW_BUTTON)) {
      findings.push({ rel, line: i + 1, rule: 'raw-button', detail: '<button>' });
    }
    for (const _ of line.matchAll(DARK_VARIANT)) {
      findings.push({ rel, line: i + 1, rule: 'dark-variant', detail: 'dark:' });
    }
  });

  return findings;
}

const ADVICE = {
  palete: '',
  palette:
    'Palette utilities belong in src/components/**. Use the shared component, or add one.',
  'raw-button': 'Use <Button> / <ButtonLink> from @/src/components/ui/Button.',
  'dark-variant':
    'The app is light-only; a per-page dark: variant produces a half-dark page. See the computor-design-spec skill.',
};

function main() {
  const argv = process.argv.slice(2);
  const all = argv.includes('--all');
  // --count prints just the violation total. Used by the PostToolUse hook to
  // compare a file against its committed version, so an edit is judged on what
  // it *added* rather than on the drift it inherited.
  const countOnly = argv.includes('--count');
  const explicit = argv.filter((a) => !a.startsWith('--'));

  if (countOnly) {
    const targets = explicit
      .map((p) => path.resolve(p))
      .filter((p) => existsSync(p) && statSync(p).isFile());
    console.log(targets.flatMap(scan).length);
    return 0;
  }

  let files;
  if (explicit.length) {
    files = explicit.map((p) => path.resolve(p)).filter((p) => existsSync(p) && statSync(p).isFile());
  } else if (all) {
    files = walk(path.join(WEB_ROOT, 'app'));
  } else {
    files = changedFiles();
  }

  files = files.filter(isGoverned);

  if (!files.length) {
    console.log('✅ check-styling: no governed files to check.');
    return 0;
  }

  const findings = files.flatMap(scan);

  if (all) {
    const byRule = {};
    const byFile = {};
    for (const f of findings) {
      byRule[f.rule] = (byRule[f.rule] ?? 0) + 1;
      byFile[f.rel] = (byFile[f.rel] ?? 0) + 1;
    }
    console.log(`Design-spec inventory across ${files.length} files in app/\n`);
    for (const [rule, n] of Object.entries(byRule).sort((a, b) => b[1] - a[1])) {
      console.log(`  ${String(n).padStart(5)}  ${rule}`);
    }
    console.log('\nWorst files:');
    Object.entries(byFile)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 15)
      .forEach(([file, n]) => console.log(`  ${String(n).padStart(5)}  ${file}`));
    console.log('\n(--all never fails; it is a report.)');
    return 0;
  }

  if (!findings.length) {
    console.log(`✅ check-styling: ${files.length} changed file(s) clean.`);
    return 0;
  }

  console.log(`❌ check-styling: ${findings.length} violation(s) in changed files\n`);
  const rules = new Set();
  for (const f of findings) {
    console.log(`  ${f.rel}:${f.line}  ${f.rule}  ${f.detail}`);
    rules.add(f.rule);
  }
  console.log();
  for (const rule of rules) console.log(`  · ${ADVICE[rule]}`);
  console.log(`\n  Escape hatch for a genuine one-off: add "${OPT_OUT} — reason" on the line or above it.`);
  console.log('  Full inventory: node scripts/check-styling.mjs --all');
  return 1;
}

process.exit(main());
