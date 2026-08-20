import { test, expect } from '@playwright/test';

// The theme has to hold in all three states the CSS is written for: an explicit
// choice either way, and the un-stamped default that follows the OS.
const CASES = [
  { name: 'system + dark OS', colorScheme: 'dark' as const, stamp: null },
  { name: 'system + light OS', colorScheme: 'light' as const, stamp: null },
  { name: 'explicit dark on a light OS', colorScheme: 'light' as const, stamp: 'dark' },
  { name: 'explicit light on a dark OS', colorScheme: 'dark' as const, stamp: 'light' },
];

for (const c of CASES) {
  test(`tokens resolve: ${c.name}`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: c.colorScheme });
    if (c.stamp) {
      await page.addInitScript((v) => localStorage.setItem('computor-theme', v), c.stamp);
    }
    await page.goto('/login');

    const read = await page.evaluate(() => {
      const s = getComputedStyle(document.documentElement);
      const names = ['--c-fg', '--c-body', '--c-muted', '--c-surface', '--c-canvas', '--c-rule', '--c-accent-wash'];
      const out: Record<string, string> = {};
      for (const n of names) out[n] = s.getPropertyValue(n).trim();
      out['body-bg'] = getComputedStyle(document.body).backgroundColor;
      out['stamp'] = document.documentElement.getAttribute('data-theme') ?? '(none)';
      return out;
    });

    // Every token must resolve to something — an empty string means the block
    // that should have defined it never applied.
    for (const [name, value] of Object.entries(read)) {
      expect(value, `${name} in ${c.name}`).not.toBe('');
    }

    const dark = c.stamp === 'dark' || (c.stamp === null && c.colorScheme === 'dark');
    // The browser normalises #ffffff to #fff, so compare on the expanded form.
    const expand = (hex: string) =>
      /^#[0-9a-f]{3}$/i.test(hex) ? '#' + [...hex.slice(1)].map((c) => c + c).join('') : hex;
    const surface = expand(read['--c-surface'].toLowerCase());
    if (dark) {
      expect(surface, 'dark surface must not be white').not.toBe('#ffffff');
    } else {
      expect(surface, 'light surface must be white').toBe('#ffffff');
    }
    console.log(`${c.name.padEnd(28)} stamp=${read['stamp'].padEnd(7)} surface=${surface} fg=${read['--c-fg']} body-bg=${read['body-bg']}`);
  });
}
