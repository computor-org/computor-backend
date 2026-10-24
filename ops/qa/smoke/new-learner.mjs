// New-learner smoke run against a QA stack (computor-org/issues#529).
//
// A brand-new synthetic learner registers through the real Keycloak form,
// reads the verification mail from the Mailpit API, follows the link, sets the
// password, joins "Data Science mit Python – Grundlagen" from the public reader
// and launches the VS Code workspace until code-server shows the Computor
// extension. Every step is saved as a PNG.
//
//   QA_ORIGIN=http://localhost:18480 QA_MAILPIT=http://127.0.0.1:18425 \
//   QA_SCREENS=/tmp/qa-screens QA_PLAYWRIGHT_FROM=/path/with/node_modules \
//   node ops/qa/smoke/new-learner.mjs
//
// Headless only. Exit code 0 means every step passed.
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';
import { randomBytes } from 'node:crypto';

const require = createRequire(
  process.env.QA_PLAYWRIGHT_FROM ? `${process.env.QA_PLAYWRIGHT_FROM}/` : import.meta.url,
);
const { chromium } = require('playwright');

const origin = (process.env.QA_ORIGIN || 'http://localhost:18480').replace(/\/$/, '');
const mailpit = (process.env.QA_MAILPIT || 'http://127.0.0.1:18425').replace(/\/$/, '');
const screens = process.env.QA_SCREENS || './qa-screens';
const course = process.env.QA_COURSE_SLUG || 'python-beginner';
const skipWorkspace = process.env.QA_SKIP_WORKSPACE === '1';
mkdirSync(screens, { recursive: true });

const id = `${Date.now().toString(36)}${randomBytes(2).toString('hex')}`;
const learner = {
  username: `qa-neu-${id}`,
  email: `qa-neu-${id}@example.com`,
  firstName: 'Nora',
  lastName: 'Neuling',
  password: `Qa-${randomBytes(9).toString('base64url')}`,
};

let step = 0;
async function shot(page, name) {
  step += 1;
  const file = `${screens}/${String(step).padStart(2, '0')}-${name}.png`;
  await page.screenshot({ path: file, fullPage: false });
  console.log(`[smoke] ${file}`);
}

async function verificationLink(email, timeoutMs = 60000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const search = await fetch(`${mailpit}/api/v1/search?query=${encodeURIComponent(`to:"${email}"`)}`);
    const { messages = [] } = await search.json();
    if (messages.length) {
      const message = await (await fetch(`${mailpit}/api/v1/message/${messages[0].ID}`)).json();
      const links = (message.Text || '').match(/https?:\/\/\S+/g) || [];
      const link = links.find((l) => l.includes('action-token'));
      if (link) return { link: link.replace(/[.,)]+$/, ''), subject: message.Subject };
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error(`no verification mail for ${email} in Mailpit`);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  locale: 'de-DE',
});
const page = await context.newPage();
page.setDefaultTimeout(60000);

try {
  // 1. Public reader of the course, then "Anmelden und beitreten".
  await page.goto(`${origin}/learn/${course}`);
  await page.getByText('Anmelden und beitreten').first().waitFor();
  await shot(page, 'public-reader');
  await page.getByText('Anmelden und beitreten').first().click();

  // 2. Keycloak sign-in page, then its registration link.
  await page.waitForURL(/\/auth\/realms\/computor\//);
  await shot(page, 'keycloak-sign-in');
  await page.locator('a[href*="login-actions/registration"]').first().click();
  await page.locator('#kc-register-form').waitFor();

  // 3. Profile-only signup form (email first, no password yet: issues#441).
  await page.fill('input[name=username]', learner.username);
  await page.fill('input[name=email]', learner.email);
  await page.fill('input[name=firstName]', learner.firstName);
  await page.fill('input[name=lastName]', learner.lastName);
  if (await page.locator('#kc-register-form input[name=password]').count()) {
    throw new Error('registration form asks for a password; expected email-first signup');
  }
  // The ALTCHA widget solves its proof of work on load.
  await page.waitForFunction(() => {
    const input = document.querySelector('input[name=altcha]');
    return input && input.value && input.value.length > 20;
  }, null, { timeout: 60000 });
  await shot(page, 'registration-form');
  await page.locator('#kc-register-form [type=submit]').click();

  // 4. Terms of Use (computor.at 1.2), then "verify your email".
  const accept = page.locator('#kc-accept, input[name=accept], button[name=accept]');
  await accept.first().waitFor({ timeout: 30000 });
  await shot(page, 'terms');
  await accept.first().click();
  await page.waitForLoadState('networkidle');
  await shot(page, 'verify-email-notice');

  // 5. The verification mail, read from Mailpit's API only.
  const { link, subject } = await verificationLink(learner.email);
  console.log(`[smoke] mail "${subject}" -> ${link.slice(0, 80)}...`);
  await page.goto(link);
  // Keycloak may first ask to confirm the action in this browser.
  const proceed = page.getByRole('link', { name: /hier|here|weiter|proceed/i });
  if (await proceed.count()) await proceed.first().click();

  // 6. Password is set after verification.
  await page.locator('input[name=password-new]').waitFor();
  await shot(page, 'set-password');
  await page.fill('input[name=password-new]', learner.password);
  await page.fill('input[name=password-confirm]', learner.password);
  await page.locator('[type=submit]').first().click();

  // 7. Back in the web UI, signed in.
  await page.waitForURL((url) => url.origin === origin && !url.pathname.startsWith('/auth'), { timeout: 60000 });
  await page.waitForLoadState('networkidle');
  await shot(page, 'signed-in');

  // 8. Join Grundlagen from the catalog.
  if (!page.url().includes('/courses/catalog')) await page.goto(`${origin}/courses/catalog`);
  const card = page.locator('div', { hasText: 'Grundlagen' }).filter({ has: page.getByRole('button', { name: 'Kurs beitreten' }) }).last();
  await card.getByRole('button', { name: 'Kurs beitreten' }).waitFor();
  await shot(page, 'catalog');
  await card.getByRole('button', { name: 'Kurs beitreten' }).click();
  const confirm = page.getByRole('dialog').getByRole('button', { name: /beitreten/i });
  if (await confirm.count()) {
    await shot(page, 'join-confirm');
    await confirm.last().click();
  }
  await page.waitForURL(/\/courses\/[0-9a-f-]{36}/, { timeout: 60000 });
  await page.waitForLoadState('networkidle');
  await page.getByText('Wird geladen').first().waitFor({ state: 'detached', timeout: 60000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await shot(page, 'course-page');

  if (!skipWorkspace) {
    // 9. Launch the managed VS Code workspace (opens a new tab).
    const launch = page.getByRole('button', { name: /Arbeitsumgebung starten|Starten/ }).first();
    const [tab] = await Promise.all([context.waitForEvent('page'), launch.click()]);
    await tab.setViewportSize({ width: 1440, height: 900 });
    await tab.waitForLoadState();
    await shot(tab, 'workspace-launch');
    // code-server's workbench, then the Computor activity bar entry.
    await tab.locator('.monaco-workbench').waitFor({ timeout: 600000 });
    await tab.locator('.activitybar [aria-label*="Computor"], .activitybar [aria-label*="computor"]')
      .first().waitFor({ timeout: 300000 });
    await tab.waitForTimeout(5000);
    await shot(tab, 'vscode-workbench');
    // Open the first unit in the course tree.
    await tab.getByText('Woche 1', { exact: true }).first().click().catch(() => {});
    await tab.waitForTimeout(4000);
    await shot(tab, 'vscode-course-tree');
  }
  console.log(`[smoke] PASS learner=${learner.email}`);
} catch (error) {
  await shot(page, 'failure').catch(() => {});
  for (const p of context.pages()) if (p !== page) await shot(p, 'failure-tab').catch(() => {});
  console.error(`[smoke] FAIL at step ${step}: ${error.stack || error}`);
  process.exitCode = 1;
} finally {
  await browser.close();
}
