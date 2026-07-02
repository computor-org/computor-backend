'use client';

import type { AnalyticsCourseSummary } from '@/src/api/analytics';
import { formatCount, formatDateTime, formatGrade, formatPercent } from './format';

/**
 * Course checkpoint headline: the numbers a lecturer reads first. Submitted and
 * graded coverage are the load-bearing figures, so they get the prominent
 * cards; the rest are supporting context.
 */
export default function SummaryCards({ summary }: { summary: AnalyticsCourseSummary }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4" data-testid="analytics-summary">
      <BigStat
        label="Submitted"
        value={formatPercent(summary.submitted_percentage)}
        sub={`${formatCount(summary.total_submitted_assignments)} / ${formatCount(
          summary.total_max_assignments,
        )} assignments`}
        accent="emerald"
      />
      <BigStat
        label="Graded"
        value={formatPercent(summary.graded_percentage)}
        sub={`${formatCount(summary.total_graded_assignments)} / ${formatCount(
          summary.total_max_assignments,
        )} assignments`}
        accent="blue"
      />
      <SmallStat label="Students" value={formatCount(summary.total_students)} />
      <SmallStat label="Average grade" value={formatGrade(summary.average_grading)} />
      <SmallStat
        label="Latest submission"
        value={formatDateTime(summary.latest_submission_at)}
        wide
      />
      <SmallStat
        label="Submission cutoff"
        value={formatDateTime(summary.submission_cutoff)}
        wide
      />
      <SmallStat label="Grading cutoff" value={formatDateTime(summary.grading_cutoff)} wide />
    </div>
  );
}

const ACCENT: Record<string, string> = {
  emerald: 'text-emerald-700',
  blue: 'text-blue-700',
};

function BigStat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub: string;
  accent: keyof typeof ACCENT | string;
}) {
  return (
    <div className="rounded-lg border-2 border-gray-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className={`mt-1 text-3xl font-bold tabular-nums ${ACCENT[accent] ?? 'text-gray-900'}`}>
        {value}
      </p>
      <p className="mt-1 text-xs text-gray-500">{sub}</p>
    </div>
  );
}

function SmallStat({
  label,
  value,
  wide,
}: {
  label: string;
  value: string;
  wide?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border border-gray-200 bg-white p-4 ${wide ? 'col-span-2 md:col-span-2' : ''}`}
    >
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-gray-900">{value}</p>
    </div>
  );
}
