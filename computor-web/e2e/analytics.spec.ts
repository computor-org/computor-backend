import { expect, test } from '@playwright/test';
import { MEMBER_ID, analyticsUrl, setupAnalytics } from './fixtures';

test.describe('lecturer analytics', () => {
  test('dashboard shows local and analytics snapshot courses', async ({ page }) => {
    await setupAnalytics(page, { role: '_lecturer', scenario: 'data' });
    await page.goto('/dashboard');

    await expect(page.getByText('Local Blue Course')).toBeVisible();
    await expect(page.getByText('Test Course')).toBeVisible();
    await expect(page.getByText('Local', { exact: true })).toBeVisible();
    await expect(page.getByText('Analytics snapshot')).toBeVisible();
    await expect(page.getByText('Source green')).toBeVisible();
  });

  test('lecturer sees the checkpoint, opens a timeline, and updates data', async ({ page }) => {
    await setupAnalytics(page, { role: '_lecturer', scenario: 'data' });
    await page.goto(analyticsUrl());

    // Headline checkpoint figures (scoped to the summary, the table repeats some).
    await expect(page.getByRole('heading', { name: 'Course Analytics' })).toBeVisible();
    const summary = page.getByTestId('analytics-summary');
    await expect(summary.getByText('70%')).toBeVisible(); // submitted
    await expect(summary.getByText('50%')).toBeVisible(); // graded

    // Master list is names only: no matrikelnummer, no flags, no scores. A
    // passing student must not read another student's standing off the screen.
    const roster = page.getByTestId('analytics-roster');
    await expect(roster.getByText('Ada Lovelace')).toBeVisible();
    await expect(roster.getByText('01234567')).toHaveCount(0);
    await expect(roster.getByText('Burst')).toHaveCount(0);

    await expect(page.getByText('Select a student to see their evidence.')).toBeVisible();
    await expect(page.getByTestId('analytics-timeline')).toHaveCount(0);
    await expect(page.getByRole('heading', { name: 'Examples' })).toHaveCount(0);
    const findText = page.getByTestId('analytics-browser-find-text');
    await expect(findText).toContainText('Week 2 · Loops');
    await expect(findText).toContainText('week_2.loops');
    await expect(findText).toContainText('cc-2');
    await expect(findText).toContainText('week_1.easter_formula');
    await expect(findText).toContainText('easter_formula@v1.0.0');
    await expect(findText).toContainText('week 1 easter formula');
    await expect(findText).toBeVisible();
    await expect
      .poll(() => page.evaluate(() => window.find('week_2.loops', false, false, true)))
      .toBe(true);
    await expect
      .poll(() => page.evaluate(() => window.find('week_1.easter_formula', false, false, true)))
      .toBe(true);
    await expect
      .poll(() => page.evaluate(() => window.find('easter', false, false, true)))
      .toBe(true);

    // Roster row -> per-student timeline (the signature curve).
    const searchBox = roster.getByRole('searchbox', { name: 'Search students' });
    await searchBox.fill('loops');
    await expect(roster.getByText('Ada Lovelace')).toHaveCount(0);
    await expect(roster.getByText('No students match “loops”.')).toBeVisible();
    await searchBox.fill('ada');
    const row = roster.getByText('Ada Lovelace');
    await expect(row).toBeVisible();
    await expect(roster.getByText('Grace Hopper')).toHaveCount(0);
    await page.keyboard.press('ArrowDown');
    await expect(row).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(new RegExp(`/lecturer/analytics\\?student=${MEMBER_ID}$`));
    const timeline = page.getByTestId('analytics-timeline');
    await expect(timeline).toBeVisible();
    await expect(
      timeline.getByRole('img', { name: 'Cumulative official submissions over time' }),
    ).toBeVisible();

    // Detail leads with the score-pass summary, then the per-example evidence
    // table (with a tutor comment), which replaced the old flat event log.
    await expect(timeline.getByText('8/10 standard examples')).toBeVisible();
    await expect(timeline.getByRole('link', { name: 'Week 1 · Intro' })).toBeVisible();
    await expect(timeline.getByText(/asked to explain in lab/)).toBeVisible();

    await page.getByRole('link', { name: 'Back to Test Course' }).click();
    await expect(page).toHaveURL(/\/lecturer\/analytics$/);
    await expect(page.getByText('Select a student to see their evidence.')).toBeVisible();
    await expect(page.getByTestId('analytics-timeline')).toHaveCount(0);

    await row.click();
    await expect(page).toHaveURL(new RegExp(`/lecturer/analytics\\?student=${MEMBER_ID}$`));

    // Clicking an example opens its full source page (syntax-highlighted), and
    // "Back" returns to this student's detail.
    await page.getByTestId('analytics-timeline').getByRole('link', { name: 'Week 2 · Loops' }).click();
    await expect(page).toHaveURL(/\/lecturer\/analytics\/examples\/cc-2\?student=/);
    await expect(page.getByText('def loops(values):')).toBeVisible();
    await page.getByRole('button', { name: 'test_loops.py' }).click();
    await expect(page.getByText('def test_loops():')).toBeVisible();
    await page.getByRole('link', { name: /Back to student/ }).click();
    await expect(
      page.getByTestId('analytics-timeline').getByText('8/10 standard examples'),
    ).toBeVisible();

    // Update button triggers a job and polls it to completion.
    const refresh = page.getByTestId('analytics-refresh');
    await expect(refresh).toBeVisible();
    await refresh.click();
    await expect(page.getByTestId('analytics-job-status')).toContainText('completed', {
      timeout: 15_000,
    });
  });

  test('tutor can read but cannot update', async ({ page }) => {
    await setupAnalytics(page, { role: '_tutor', scenario: 'data' });
    await page.goto(analyticsUrl());

    await expect(page.getByTestId('analytics-roster').getByText('Ada Lovelace')).toBeVisible();
    await expect(page.getByTestId('analytics-refresh')).toHaveCount(0);
  });

  test('does not block the dashboard on the browser-find example text', async ({ page }) => {
    await setupAnalytics(page, { role: '_lecturer', scenario: 'data', exampleDelayMs: 3_000 });
    await page.goto(analyticsUrl());

    await expect(page.getByTestId('analytics-summary')).toBeVisible({ timeout: 2_000 });
    await expect(page.getByTestId('analytics-roster').getByText('Ada Lovelace')).toBeVisible();
    await expect(page.getByText('Loading analytics…')).toHaveCount(0);
    await expect(page.getByTestId('analytics-browser-find-text')).toContainText('week_2.loops', {
      timeout: 5_000,
    });
  });

  test('shows an empty state when no snapshot exists', async ({ page }) => {
    await setupAnalytics(page, { role: '_lecturer', scenario: 'empty' });
    await page.goto(analyticsUrl());

    await expect(page.getByRole('heading', { name: 'No snapshot yet' })).toBeVisible();
    // Lecturer still gets the update control to run the first import.
    await expect(page.getByTestId('analytics-refresh')).toBeVisible();
  });
});
