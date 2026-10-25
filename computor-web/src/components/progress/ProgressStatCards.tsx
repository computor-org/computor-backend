'use client';

import StatGrid, { StatCard } from '@/src/components/ui/StatGrid';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import type { CourseMemberGradingsList } from 'types/generated';

const COPY = {
  de: {
    students: 'Studierende',
    average: 'Durchschnittlicher Fortschritt',
    completed: 'Abgeschlossen',
    atRisk: 'Gefährdet',
    atRiskHint: 'unter 25 % Fortschritt',
    inactive: 'Inaktiv',
    inactiveHint: 'keine Abgabe in 14 Tagen',
  },
  en: {
    students: 'Students',
    average: 'Average progress',
    completed: 'Completed',
    atRisk: 'At risk',
    atRiskHint: 'under 25% progress',
    inactive: 'Inactive',
    inactiveHint: 'no submission in 14 days',
  },
};

function daysSince(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  return Math.floor((Date.now() - new Date(dateStr).getTime()) / (1000 * 60 * 60 * 24));
}

/**
 * The cohort summary above the grading roster.
 *
 * Replaces the tinted-background tiles this page used to draw itself. The
 * numbers are the same; the strip now looks like every other summary strip in
 * the app, and the tone is carried by the figure rather than by five different
 * background washes competing with the charts beneath them.
 */
export default function ProgressStatCards({ students }: { students: CourseMemberGradingsList[] }) {
  const t = COPY[useUiLanguage()];
  const total = students.length;
  const avgProgress =
    total > 0
      ? Math.round(students.reduce((sum, s) => sum + s.overall_progress_percentage, 0) / total)
      : 0;
  const completed = students.filter((s) => s.overall_progress_percentage >= 100).length;
  const atRisk = students.filter((s) => s.overall_progress_percentage < 25).length;
  const inactive = students.filter((s) => {
    const days = daysSince(s.latest_submission_at);
    return days === null || days > 14;
  }).length;

  return (
    <StatGrid columns={5}>
      <StatCard label={t.students} value={total} />
      <StatCard label={t.average} value={`${avgProgress}%`} tone="info" />
      <StatCard label={t.completed} value={completed} tone="success" />
      <StatCard label={t.atRisk} value={atRisk} tone="error" hint={t.atRiskHint} />
      <StatCard label={t.inactive} value={inactive} tone="warning" hint={t.inactiveHint} />
    </StatGrid>
  );
}
