import { test, expect, type Route } from '@playwright/test';

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}
for (const language of ['de', 'en']) {
  for (const width of [390, 1440]) {
    for (const colorScheme of ['light', 'dark'] as const) {
      test(`${language} ${width} ${colorScheme}: select new versions then release`, async ({ page }) => {
        await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
        await page.emulateMedia({ colorScheme });
        await page.addInitScript(({ language, colorScheme }) => {
          sessionStorage.setItem('auth_user', JSON.stringify({ id: 'lect', username: 'lect', email: 'lect@example.org', role: 'user', systemRoles: ['admin'], language }));
          sessionStorage.setItem('auth_provider', 'sso');
          localStorage.setItem('theme', colorScheme);
        }, { language, colorScheme });
        let failUpgrade = language === 'de' && width === 1440 && colorScheme === 'light';
        let failRelease = true;
        const internalError = 'Permission denied /tmp/private-course on http://computor-git';
        let selected = false;
        let released = false;
        const upgrades: unknown[] = [];
        await page.route('http://localhost:8000/**', route => {
          const path = new URL(route.request().url()).pathname;
          if (path.startsWith('/user/views')) return json(route, ['lecturer', 'admin']);
          if (path === '/user/scopes') return json(route, { is_admin: true, course: { demo: ['_lecturer'] } });
          if (path === '/user') return json(route, { id: 'lect', user_roles: [], profile: { language_code: language } });
          if (path === '/courses/demo') return json(route, { id: 'demo', title: 'Python', path: 'demo' });
          if (path === '/lecturers/course-contents') return json(route, [
            { id: 'unit', title: 'Week 1', path: 'demo.week1', is_submittable: false, course_content_type_id: 'weekly', has_deployment: false },
            { id: 'missing', title: 'Missing example', path: 'demo.missing', is_submittable: true, course_content_type_id: 'beginner', has_deployment: false },
            { id: 'changed', title: 'Taylor', path: 'demo.taylor', is_submittable: true, course_content_type_id: 'beginner', has_deployment: true, deployment_status: released ? 'deployed' : selected ? 'pending' : 'deployed', deployment: { has_newer_version: !selected } },
            { id: 'current', title: 'Constants', path: 'demo.constants', is_submittable: true, has_deployment: true, deployment_status: 'deployed', deployment: { has_newer_version: false } },
          ]);
          if (path === '/lecturers/courses/demo/upgrade-versions') {
            if (failUpgrade) { failUpgrade = false; return json(route, { message: 'Server unavailable' }, 503); }
            upgrades.push(route.request().postDataJSON()); selected = true;
            return json(route, { total_requested: 1, total_upgraded: 1, total_skipped: 0, total_failed: 0, results: [] });
          }
          if (path === '/system/courses/demo/generate-student-template') {
            if (failRelease) { failRelease = false; return json(route, { detail: internalError }, 503); }
            released = true; return json(route, {});
          }
          if (path === '/course-contents/changed' && route.request().method() === 'PATCH') return json(route, { message: internalError }, 503);
          if (path === '/course-content-types') return json(route, [
            { id: 'weekly', slug: 'weekly', title: language === 'de' ? 'Woche' : 'Week' },
            { id: 'beginner', slug: 'beginner', title: language === 'de' ? 'Aufgabe' : 'Assignment' },
          ]);
          if (path.startsWith('/messages')) return json(route, []);
          return json(route, {});
        });
        await page.goto('/courses/demo/lecturer/assignments');
        const select = page.getByRole('button', { name: language === 'de' ? 'Neueste Versionen auswählen (1)' : 'Select latest versions (1)', exact: true });
        await expect(select).toBeVisible();
        // A normal unit has no example by design, but an assignment without one
        // must still count as needing attention.
        const missingStat = page.getByText(language === 'de' ? 'Fehlgeschlagen / ohne Beispiel' : 'Failed / none', { exact: true }).locator('..');
        await expect(missingStat).toHaveText(language === 'de' ? '1Fehlgeschlagen / ohne Beispiel' : '1Failed / none');
        await expect(page.getByText(language === 'de' ? 'Woche' : 'Week', { exact: true })).toBeVisible();
        await expect(page.getByText(language === 'de' ? 'Aufgabe' : 'Assignment', { exact: true }).first()).toBeVisible();
        await expect(page.getByText('weekly', { exact: true })).toHaveCount(0);
        await expect(page.getByText('beginner', { exact: true })).toHaveCount(0);
        if (width === 390) {
          const collapse = page.getByRole('button', { name: language === 'de' ? 'Seitenleiste einklappen' : 'Collapse sidebar', exact: true });
          if (await collapse.isVisible()) await collapse.click();
          await expect.poll(async () => (await page.getByRole('complementary').boundingBox())?.width).toBe(64);
        }
        await select.scrollIntoViewIfNeeded();
        await page.screenshot({ path: `${process.env.QA_SCREENS ?? '/tmp/lecturer-screens'}/assignments-${language}-${width}-${colorScheme}.png`, fullPage: true });
        await select.click();
        if (language === 'de' && width === 1440 && colorScheme === 'light') {
          await expect(page.getByRole('status')).toContainText('Die neueren Versionen konnten nicht ausgewählt werden.');
          expect(released).toBe(false);
          await select.click();
        }
        expect(upgrades).toEqual([{ course_content_ids: ['changed'] }]);
        await expect(select).toHaveCount(0);
        await expect(page.getByRole('status')).toContainText(language === 'de' ? 'Versionen ausgewählt: 1' : 'Versions selected: 1');
        const release = page.getByRole('button', { name: language === 'de' ? 'Alle ausstehenden veröffentlichen (1)' : 'Release all pending (1)', exact: true });
        await release.click();
        await expect(page.getByRole('status')).toContainText(language === 'de' ? 'Veröffentlichung fehlgeschlagen (HTTP 503)' : 'Release failed (HTTP 503)');
        await expect(page.getByRole('status')).toContainText(language === 'de' ? 'Versuch es noch einmal.' : 'Try again.');
        await expect(page.getByRole('status')).not.toContainText(internalError);
        expect(released).toBe(false);
        await release.click();
        await expect(page.getByRole('status')).toContainText(language === 'de' ? 'Veröffentlichung gestartet' : 'Release started');
        expect(released).toBe(true);
        const visibilityButton = page.getByRole('button', { name: language === 'de' ? 'Ausblenden' : 'Hide', exact: true });
        const assignmentRow = page.locator('div')
          .filter({ has: page.getByText('Taylor', { exact: true }) })
          .filter({ has: visibilityButton })
          .last();
        await assignmentRow.getByRole('button', { name: language === 'de' ? 'Ausblenden' : 'Hide', exact: true }).click();
        await expect(page.getByRole('status')).toContainText(language === 'de' ? 'Die Sichtbarkeit konnte nicht geändert werden.' : 'Could not change visibility');
        await expect(page.getByRole('status')).toContainText('HTTP 503');
        await expect(page.getByRole('status')).toContainText(language === 'de' ? 'Versuch es noch einmal.' : 'Try again.');
        await expect(page.getByRole('status')).not.toContainText(internalError);
      });
    }
  }
}

for (const language of ['de', 'en']) {
  test(`${language}: example ZIP upload uses the selected repository and completes`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const JSZip = (await import('jszip')).default;
    const zip = new JSZip();
    zip.file('changed/meta.yaml', 'slug: synthetic.example\nversion: 2.0\ntitle: Synthetic\n');
    zip.file('changed/README.md', 'Synthetic public fixture.');
    zip.file('unchanged/meta.yaml', 'slug: synthetic.unchanged\nversion: 1.0\ntitle: Unchanged\n');
    await page.addInitScript(language => {
      sessionStorage.setItem('auth_user', JSON.stringify({ id: 'admin', role: 'user', systemRoles: ['admin'], language }));
      sessionStorage.setItem('auth_provider', 'sso');
    }, language);
    const uploads: unknown[] = [];
    await page.route('http://localhost:8000/**', route => {
      const path = new URL(route.request().url()).pathname;
      if (path.startsWith('/user/views')) return json(route, ['admin']);
      if (path === '/user/scopes') return json(route, { is_admin: true });
      if (path === '/user') return json(route, { id: 'admin', user_roles: [], profile: { language_code: language } });
      if (path === '/example-repositories') return json(route, [{ id: 'default', name: 'Default Examples', source_type: 'minio' }]);
      if (path === '/examples/upload') {
        const body = route.request().postDataJSON(); uploads.push(body);
        if (body.directory === 'unchanged') return json(route, { error_code: 'VERSION_001', message: 'This version already exists.' }, 400);
        return json(route, { version_tag: '2.0' });
      }
      return json(route, []);
    });
    await page.goto('/examples/upload');
    await expect(page.getByRole('heading', { name: language === 'de' ? 'Beispiele hochladen' : 'Upload examples' })).toBeVisible();
    await expect(page.getByRole('combobox')).toHaveValue('default');
    await page.locator('input[type=file]').setInputFiles({ name: 'synthetic.zip', mimeType: 'application/zip', buffer: await zip.generateAsync({ type: 'nodebuffer' }) });
    await page.getByRole('button', { name: language === 'de' ? 'Hochladen 2' : 'Upload 2', exact: true }).click();
    await expect(page.getByRole('button', { name: language === 'de' ? 'Fertig' : 'Done', exact: true })).toBeVisible();
    const collapse = page.getByRole('button', { name: language === 'de' ? 'Seitenleiste einklappen' : 'Collapse sidebar', exact: true });
    if (await collapse.isVisible()) await collapse.click();
    await expect.poll(async () => (await page.getByRole('complementary').boundingBox())?.width).toBe(64);
    await page.screenshot({ path: `${process.env.QA_SCREENS ?? '/tmp/lecturer-screens'}/upload-${language}-390-light.png`, fullPage: true });
    expect(uploads).toHaveLength(2);
    await expect(page.getByRole('status')).toContainText(language === 'de' ? 'Bereits vorhanden: 1' : 'Already exists: 1');
    await expect(page.getByText('This version already exists.', { exact: true })).toHaveCount(0);
    expect(uploads[0]).toMatchObject({ repository_id: 'default' });
    await expect(page.getByText(language === 'de' ? 'hochgeladen v2.0' : 'uploaded v2.0', { exact: true })).toBeVisible();
  });
}
