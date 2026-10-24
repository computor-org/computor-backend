// Returning-learner check against a QA stack (computor-org/issues#529).
//
// Signs in as the seeded returning learner and saves the dashboard, the
// workspace list and the Grundlagen course page, where the seeded state
// (results, one at 0 %, an open assignment, a stopped workspace) must show.
//
//   QA_ORIGIN=http://localhost:18480 QA_SCREENS=/tmp/qa-screens \
//   QA_RETURNING_EMAIL=... QA_RETURNING_PASSWORD=... \
//   QA_PLAYWRIGHT_FROM=/path/with/node_modules node ops/qa/smoke/returning-learner.mjs
//
// The credentials are in QA_HOME/credentials.env on the QA host.
import { createRequire } from 'node:module';
import { mkdirSync } from 'node:fs';

const require = createRequire(
  process.env.QA_PLAYWRIGHT_FROM ? `${process.env.QA_PLAYWRIGHT_FROM}/` : import.meta.url,
);
const { chromium } = require('playwright');

const origin = (process.env.QA_ORIGIN || 'http://localhost:18480').replace(/\/$/, '');
const screens = process.env.QA_SCREENS || './qa-screens';
const email = process.env.QA_RETURNING_EMAIL;
const password = process.env.QA_RETURNING_PASSWORD;
if (!email || !password) throw new Error('set QA_RETURNING_EMAIL and QA_RETURNING_PASSWORD');
mkdirSync(screens, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, locale: 'de-DE' });
const page = await context.newPage();
page.setDefaultTimeout(60000);
let step = 0;
const shot = async (name) => {
  step += 1;
  const file = `${screens}/r${String(step).padStart(2, '0')}-${name}.png`;
  await page.screenshot({ path: file });
  console.log(`[smoke] ${file}`);
};
const settle = async () => {
  await page.waitForLoadState('networkidle');
  await page.getByText('Wird geladen').first().waitFor({ state: 'detached' }).catch(() => {});
  await page.waitForTimeout(1500);
};

try {
  await page.goto(`${origin}/login`);
  await page.waitForURL(/\/auth\/realms\/computor\//);
  await page.fill('input[name=username]', email);
  await page.fill('input[name=password]', password);
  await page.locator('[type=submit]').first().click();
  await page.waitForURL((url) => url.origin === origin && !url.pathname.startsWith('/auth'));
  await settle();
  await shot('dashboard');
  await page.goto(`${origin}/workspaces`);
  await settle();
  await shot('workspaces');
  await page.goto(`${origin}/courses`);
  await settle();
  await page.getByText('Data Science mit Python – Grundlagen').first().click();
  await page.waitForURL(/\/courses\/[0-9a-f-]{36}/);
  await settle();
  await shot('course-page');
  console.log('[smoke] PASS');
} catch (error) {
  await shot('failure').catch(() => {});
  console.error(`[smoke] FAIL at step ${step}: ${error.stack || error}`);
  process.exitCode = 1;
} finally {
  await browser.close();
}
