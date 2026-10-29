import { test, expect } from '@playwright/test';
import { fixedDocumentLanguage } from '../src/utils/requestLanguage';

// A legal text with one fixed language took the reader's language in the
// server-rendered <html lang> and was corrected only after hydration, so a
// screen reader or crawler without JavaScript read /privacy/en as German.

const FIXED: [string, 'de' | 'en'][] = [
  ['/privacy', 'de'], ['/privacy/en', 'en'],
  ['/terms', 'de'], ['/terms/en', 'en'],
  ['/terms/changes', 'de'], ['/terms/en/changes', 'en'],
];

for (const [path, lang] of FIXED) {
  const reader = lang === 'de' ? 'en-US' : 'de-AT';
  test(`${path} is served as lang="${lang}" to a ${reader} reader`, async ({ request }) => {
    const response = await request.get(path, { headers: { 'Accept-Language': reader } });
    expect(response.ok()).toBe(true);
    expect(await response.text()).toMatch(new RegExp(`<html lang="${lang}"`));
  });
}

test('pages without a fixed language keep the reader\'s language', async ({ request }) => {
  const response = await request.get('/impressum', { headers: { 'Accept-Language': 'en-US' } });
  expect(await response.text()).toMatch(/<html lang="en"/);
});

test('the route table ignores a trailing slash and knows no other page', () => {
  expect(fixedDocumentLanguage('/privacy/en/')).toBe('en');
  expect(fixedDocumentLanguage('/impressum')).toBeNull();
});
