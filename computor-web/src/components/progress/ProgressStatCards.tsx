'use client';

import StatGrid, { StatCard } from '@/src/components/ui/StatGrid';
import type { CourseMemberGradingsList } from 'types/generated';

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
      <StatCard label="Students" value={total} />
      <StatCard label="Average progress" value={`${avgProgress}%`} tone="info" />
      <StatCard label="Completed" value={completed} tone="success" />
      <StatCard label="At risk" value={atRisk} tone="error" hint="under 25% progress" />
      <StatCard label="Inactive" value={inactive} tone="warning" hint="no submission in 14 days" />
    </StatGrid>
  );
}
