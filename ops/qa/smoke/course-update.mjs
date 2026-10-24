// Course update rehearsal on a QA stack (computor-org/issues#529).
//
// Drives the web UI the way people do on computor.at, one phase per run:
//
//   QA_PHASE=learners   both seeded learners: dashboard, course page, the first
//                       assignment's text, workspaces, and (QA_WORKSPACE=1) the
//                       VS Code workspace with the course tree; run before and
//                       after the update with QA_LABEL=before|after
//   QA_PHASE=update     the admin uploads QA_EXAMPLES_ZIP (ops/qa/fetch_examples.sh)
//                       on Examples -> Upload, then opens Grundlagen's
//                       Lecturer -> Assignments page and releases what it offers;
//                       using the native select-latest and publish controls.
//
// Every step saves a screenshot and prints the texts a person would read, so
// the run doubles as the rehearsal protocol (ops/qa/README.md).
//
//   QA_ORIGIN=http://localhost:18480 QA_SCREENS=/tmp/rehearsal QA_PHASE=update \
//   QA_ADMIN_EMAIL=... QA_ADMIN_PASSWORD=... QA_EXAMPLES_ZIP=examples-<commit>.zip \
//   QA_PLAYWRIGHT_FROM=/path/with/node_modules node ops/qa/smoke/course-update.mjs
//
// Credentials are in QA_HOME/credentials.env on the QA host. The personal
// tester's account (QA_PERSONAL_*) is never used here.
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';
import { verifySnapshots } from './course-update-state.mjs';

const require = createRequire(
  process.env.QA_PLAYWRIGHT_FROM ? `${process.env.QA_PLAYWRIGHT_FROM}/` : import.meta.url,
);
const { chromium } = require('playwright');

const origin = (process.env.QA_ORIGIN || 'http://localhost:18480').replace(/\/$/, '');
const screens = process.env.QA_SCREENS || './qa-screens';
const phase = process.env.QA_PHASE || 'learners';
const label = process.env.QA_LABEL || phase;
const locale = process.env.QA_LOCALE || 'de-DE';
const course = 'Data Science mit Python – Grundlagen';
mkdirSync(screens, { recursive: true });

const shellQuote = value => `'${value.replaceAll("'", "'\\''")}'`;
const filesProgram = readFileSync(new URL('./course-update-files.py', import.meta.url), 'utf8');
const filesEncoded = Buffer.from(filesProgram).toString('base64');
const browser = await chromium.launch({ headless: true });
let step = 0;
const started = Date.now();
const say = (text) => console.log(`[rehearsal +${Math.round((Date.now() - started) / 1000)}s] ${text}`);
const shot = async (page, name) => {
  step += 1;
  const file = `${screens}/${label}-${String(step).padStart(2, '0')}-${name}.png`;
  await page.screenshot({ path: file });
  say(`screenshot ${file}`);
};
const settle = async (page) => {
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.getByText(/Wird geladen|Loading/).first().waitFor({ state: 'detached', timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(1500);
};
// The visible text of the main area, condensed, as the protocol of what a person reads.
const read = async (page, what) => {
  const text = await page.locator('main').first().innerText().catch(() => page.locator('body').innerText());
  say(`${what}: ${text.replace(/\s+/g, ' ').trim().slice(0, 900)}`);
};

async function signIn(email, password) {
  assert.ok(email && password, 'QA sign-in credentials required');
  assert.ok(!/chris-qa/i.test(email), 'personal QA persona must never be used');
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale });
  const page = await context.newPage();
  page.setDefaultTimeout(60000);
  await page.goto(`${origin}/login`);
  await page.waitForURL(/\/auth\/realms\/computor\//);
  await page.fill('input[name=username]', email);
  await page.fill('input[name=password]', password);
  await page.locator('[type=submit]').first().click();
  await page.waitForURL((url) => url.origin === origin && !url.pathname.startsWith('/auth'));
  await settle(page);
  return { context, page };
}

async function openCourse(page, title = course) {
  await page.goto(`${origin}/courses`);
  await settle(page);
  await page.getByText(title, { exact: true }).first().click();
  await page.waitForURL(/\/courses\/[0-9a-f-]{36}/);
  await settle(page);
  return page.url().match(/\/courses\/([0-9a-f-]{36})/)[1];
}

// Snapshots contain only QA identities and hashes, never tokens or exercise sources.
const evidence = { refs: {}, learners: {} };
for (const name of ['BACKEND', 'EXAMPLES', 'MIRROR']) {
  const ref = process.env[`QA_${name}_COMMIT`];
  assert.match(ref || '', /^[0-9a-f]{40}$/, `set full QA_${name}_COMMIT`);
  evidence.refs[name] = ref;
}
async function api(key, path) {
  const token = process.env[`QA_${key}_API_TOKEN`];
  assert.ok(token, `set QA_${key}_API_TOKEN`);
  const response = await fetch(`${origin}/api${path}`, { headers: { 'X-API-Token': token } });
  assert.ok(response.ok, `${path}: HTTP ${response.status}`);
  return response.json();
}
async function capture(key, courseId, assignmentText) {
  const contents = await api(key, `/students/course-contents?course_id=${courseId}&limit=1000`);
  const assignments = contents.filter(c => c.submission_group?.id).map(c => ({
    id: c.id, path: c.path, submitted: c.submitted,
    result_count: c.result_count, submission_count: c.submission_count,
    result: c.result, group: c.submission_group,
  })).sort((a, b) => a.id.localeCompare(b.id));
  assert.ok(assignments.some(c => c.submission_count > 0 && c.result?.id), `${key}: genuine graded submission required`);
  const repository = await api(key, `/user/courses/${courseId}/repository`);
  assert.ok(repository?.id && repository?.repo_ref, `${key}: learner repository required`);
  const { workspaces = [] } = await api(key, '/coder/workspaces');
  const identities = workspaces.map(w => ({ id: w.id, name: w.name, owner_name: w.owner_name }))
    .sort((a, b) => a.name.localeCompare(b.name));
  assert.ok(identities.length && identities.every(w => w.id), `${key}: workspace identities required`);
  const artifacts = [];
  for (const assignment of assignments.filter(c => c.submission_count > 0)) {
    const rows = await api(key, `/submissions/artifacts?submission_group_id=${assignment.group.id}&limit=1000`);
    assert.ok(rows.some(a => a.submit === true), `${key}: official submitted artifacts required`);
    artifacts.push(...rows.map(a => ({ id: a.id, group: a.submission_group_id, version: a.version_identifier, submit: a.submit })));
  }
  artifacts.sort((a, b) => a.id.localeCompare(b.id));
  const deployments = await api('ADMIN', `/lecturers/courses/${courseId}/deployments`);
  assert.equal(process.env.QA_FILES_HOST, 'mailuefterl', 'set QA_FILES_HOST=mailuefterl for read-only file proof');
  assert.equal(workspaces.length, 1, 'exactly one learner workspace expected');
  const owner = workspaces[0].owner_name;
  assert.match(owner, /^[a-z0-9_-]+$/);
  const container = `coder-${owner}-${workspaces[0].name}`;
  assert.match(container, /^coder-[a-z0-9_-]+$/);
  const command = `docker exec ${container} python3 -c ${shellQuote(filesProgram)} --persona qa-${key.toLowerCase()}`;
  const files = JSON.parse(execFileSync('ssh', ['mailuefterl', command], { encoding: 'utf8', timeout: 30000 }));
  evidence.learners[key] = { courseId, assignments, artifacts, repository, files, workspaces: identities,
    deployments: deployments.deployments.map(d => ({ id: d.course_content_id, version: d.version_tag }))
      .sort((a, b) => a.id.localeCompare(b.id)),
    text_sha256: createHash('sha256').update(assignmentText).digest('hex') };
}

async function learner(key) {
  const email = process.env[`QA_${key}_EMAIL`];
  const password = process.env[`QA_${key}_PASSWORD`];
  if (!email || !password) throw new Error(`set QA_${key}_EMAIL and QA_${key}_PASSWORD`);
  const who = key.toLowerCase();
  const { context, page } = await signIn(email, password);
  await shot(page, `${who}-dashboard`);
  await read(page, `${who} dashboard`);
  const id = await openCourse(page);
  await shot(page, `${who}-course`);
  await read(page, `${who} course page`);
  // Sidebar: Studierende -> Aufgaben.
  await page.goto(`${origin}/courses/${id}/student/assignments`);
  await settle(page);
  await shot(page, `${who}-assignments`);
  await read(page, `${who} assignments`);
  await page.locator('xpath=//*[normalize-space()="Mathematische Konstanten"]/ancestor::*[.//*[normalize-space()="Öffnen"]][1]')
    .getByText('Öffnen', { exact: true }).first().click();
  await settle(page);
  await shot(page, `${who}-assignment`);
  await read(page, `${who} assignment text`);
  const assignmentText = await page.locator('main').first().innerText();
  await page.goto(`${origin}/workspaces`);
  await settle(page);
  await shot(page, `${who}-workspaces`);
  await read(page, `${who} workspaces`);
  if (process.env.QA_WORKSPACE === '1') {
    await openCourse(page);
    const launch = page.getByRole('button', { name: /^(Arbeitsumgebung starten|Arbeitsumgebung öffnen|In VS Code öffnen|Starten|Öffnen|Open in VS Code|Start workspace)$/i }).first();
    const [tab] = await Promise.all([context.waitForEvent('page'), launch.click()]);
    await tab.setViewportSize({ width: 1440, height: 900 });
    await tab.waitForLoadState();
    await tab.locator('.monaco-workbench').waitFor({ timeout: 600000 });
    await tab.locator('.activitybar [aria-label*="Computor"], .activitybar [aria-label*="computor"]')
      .first().waitFor({ timeout: 300000 });
    await tab.waitForTimeout(15000);
    await shot(tab, `${who}-vscode`);
    const week = tab.locator('.monaco-list-row').filter({ hasText: /^Woche 1(?:\s|●|$)/ }).first();
    if (await week.getAttribute('aria-expanded') !== 'true') await week.locator('.monaco-tl-twistie').click();
    await tab.waitForTimeout(8000);
    // Reading a task does not clone its files. Expand the assignment as a learner
    // does to establish the repository before capturing preservation evidence.
    const assignment = tab.locator('.monaco-list-row').filter({ hasText: 'Mathematische Konstanten' }).first();
    if (await assignment.getAttribute('aria-expanded') !== 'true') await assignment.locator('.monaco-tl-twistie').click();
    await tab.waitForTimeout(20000);
    if (label === 'before') {
      await tab.keyboard.press('F1');
      const quick = tab.locator('.quick-input-widget input');
      await quick.fill('>Terminal: Create New Terminal');
      await tab.keyboard.press('Enter');
      await tab.waitForTimeout(2000);
      const command = `python3 -c ${shellQuote(`import base64;exec(base64.b64decode('${filesEncoded}'))`)} --persona qa-${who} --prepare`;
      await tab.keyboard.type(command, { delay: 1 });
      await tab.keyboard.press('Enter');
      await tab.waitForTimeout(3000);
    } else if (label === 'after') {
      // Use the visible Student-view toolbar. Palette fuzzy matching can pick
      // the unrelated offline-mode command instead of the connected view.
      const refresh = tab.locator('.sidebar .action-label.codicon-refresh:visible');
      assert.equal(await refresh.count(), 1, 'one native Student-view Refresh control required');
      say(`${who} native Refresh: ${await refresh.getAttribute('aria-label')}`);
      await refresh.click();
      await tab.waitForTimeout(15000);
      assert.equal(await tab.locator('.monaco-dialog-box:visible').count(), 0, 'Refresh must not show an error dialog');
    }
    await shot(tab, `${who}-vscode-tree`);
    const notes = await tab.locator('.notifications-toasts .notification-list-item-message').allInnerTexts().catch(() => []);
    say(`${who} VS Code notifications: ${JSON.stringify(notes)}`);
    const tree = await tab.locator('.pane-body .monaco-list-row').allInnerTexts().catch(() => []);
    say(`${who} VS Code tree rows: ${JSON.stringify(tree.slice(0, 20))}`);
  }
  await capture(key, id, assignmentText);
  await context.close();
}

async function update() {
  const zip = process.env.QA_EXAMPLES_ZIP;
  if (!zip) throw new Error('set QA_EXAMPLES_ZIP (ops/qa/fetch_examples.sh writes it)');
  const { context, page } = await signIn(process.env.QA_ADMIN_EMAIL, process.env.QA_ADMIN_PASSWORD);

  // 1. Examples -> the repository -> Upload examples.
  await page.goto(`${origin}/examples`);
  await settle(page);
  await shot(page, 'examples');
  await read(page, 'examples page');
  await page.goto(`${origin}/example-repositories`);
  await settle(page);
  await page.getByText('Default Examples').first().click();
  await settle(page);
  await shot(page, 'example-repository');
  await page.getByRole('link', { name: /Upload examples|Beispiele hochladen/ }).click();
  await settle(page);
  await page.locator('input[type=file]').setInputFiles(zip);
  await page.getByText(/ready|bereit/i).first().waitFor({ timeout: 120000 });
  await shot(page, 'upload-discovered');
  await read(page, 'upload page after choosing the zip');
  const upload = page.getByRole('button', { name: /^(Upload|Hochladen) \d+/ });
  say(`upload button: ${await upload.innerText()}`);
  await upload.click();
  await page.getByRole('button', { name: /^(Done|Fertig)$/ }).waitFor({ timeout: 1800000 });
  await settle(page);
  await shot(page, 'upload-result');
  const rows = await page.locator('[title]').evaluateAll((els) => els.map((e) => e.getAttribute('title')).filter(Boolean));
  const tally = {};
  for (const r of rows) tally[r] = (tally[r] || 0) + 1;
  say(`upload row messages: ${JSON.stringify(tally).slice(0, 1500)}`);
  await read(page, 'upload page after upload');

  // 2. Native lecturer UI: select newer versions, then publish pending work.
  for (const path of ['python.beginner', 'python.intermediate', 'python.advanced']) {
    const matches = await api('ADMIN', `/courses?path=${path}`);
    assert.equal(matches.length, 1, `expected one ${path} course`);
    const id = await openCourse(page, matches[0].title);
    const { deployments = [] } = await api('ADMIN', `/lecturers/courses/${id}/deployments`);
    const newer = deployments.filter(d => d.has_newer_version);
    assert.ok(newer.length, 'upload produced no newer deployable versions (rejected/no-op update)');
    await page.goto(`${origin}/courses/${id}/lecturer/assignments`);
    await settle(page);
    await shot(page, 'lecturer-assignments');
    const selectLatest = page.getByRole('button', { name: /Neueste Versionen auswählen|Select latest versions/ });
    assert.ok(await selectLatest.isEnabled(), 'native select-latest control must be enabled');
    await selectLatest.click();
    const pending = page.getByRole('button', { name: /Alle ausstehenden veröffentlichen|Release all pending/ });
    await pending.waitFor();
    await pending.click();
    await shot(page, 'lecturer-release');
    // Release starts an asynchronous template workflow. Verify its visible/API
    // outcome rather than accepting a click or an optimistic toast as success.
    const deadline = Date.now() + 600000;
    let released = false;
    while (Date.now() < deadline) {
      const current = await api('ADMIN', `/lecturers/courses/${id}/deployments`);
      released = newer.every(old => current.deployments.some(d =>
        d.course_content_id === old.course_content_id && d.version_tag !== old.version_tag &&
        d.deployment_status === 'deployed'));
      if (released) break;
      await page.waitForTimeout(3000);
    }
    assert.ok(released, 'all selected versions must actually deploy');
    await page.reload();
    await settle(page);
    await shot(page, 'lecturer-released');
    say(`released changed versions for ${path}`);
  }
  await context.close();
}

try {
  if (phase === 'update') await update();
  else {
    // The public reader (/learn) shows the mirror revision the web was built with.
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale });
    const page = await context.newPage();
    await page.goto(`${origin}/learn/python-beginner/content/week_1.math_constants`);
    await settle(page);
    await shot(page, 'reader');
    await read(page, 'public reader');
    await context.close();
    await learner('RETURNING');
    await learner('SECOND');
  }
  if (phase === 'learners') {
    const file = `${screens}/${label}-state.json`;
    writeFileSync(file, `${JSON.stringify(evidence, null, 2)}\n`, { mode: 0o600 });
    if (label === 'after') {
      assert.ok(process.env.QA_BEFORE_STATE, 'set QA_BEFORE_STATE to the baseline snapshot');
      verifySnapshots(JSON.parse(readFileSync(process.env.QA_BEFORE_STATE, 'utf8')), evidence);
      say('PASS: changed revisions/text and preserved learner state');
    } else say(`CAPTURED baseline ${file}; preservation not yet verified`);
  } else say('UPDATE COMPLETED; run after snapshot to verify preservation');
} catch (error) {
  for (const ctx of browser.contexts()) for (const p of ctx.pages()) await shot(p, 'failure').catch(() => {});
  console.error(`[rehearsal] FAIL at step ${step}: ${error.stack || error}`);
  process.exitCode = 1;
} finally {
  await browser.close();
}
