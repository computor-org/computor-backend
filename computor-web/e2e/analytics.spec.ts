import { expect, test } from '@playwright/test';
import { analyticsUrl, setupAnalytics } from './fixtures';

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

    // Roster row -> per-student timeline (the signature curve).
    const row = page.getByTestId('analytics-roster').getByText('Ada Lovelace');
    await expect(row).toBeVisible();
    await row.click();
    const timeline = page.getByTestId('analytics-timeline');
    await expect(timeline).toBeVisible();
    await expect(
      timeline.getByRole('img', { name: 'Cumulative official submissions over time' }),
    ).toBeVisible();

    // Detail leads with the score-pass summary, then the per-example evidence
    // table (with a tutor comment), which replaced the old flat event log.
    await expect(timeline.getByText('8/10 standard passed')).toBeVisible();
    await expect(timeline.getByRole('link', { name: 'Week 2 · Loops' })).toBeVisible();
    await expect(timeline.getByText(/asked to explain in lab/)).toBeVisible();

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

  test('shows an empty state when no snapshot exists', async ({ page }) => {
    await setupAnalytics(page, { role: '_lecturer', scenario: 'empty' });
    await page.goto(analyticsUrl());

    await expect(page.getByRole('heading', { name: 'No snapshot yet' })).toBeVisible();
    // Lecturer still gets the update control to run the first import.
    await expect(page.getByTestId('analytics-refresh')).toBeVisible();
  });
});
