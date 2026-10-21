'use client';

import { useMemo, useState } from 'react';
import Panel from '@/src/components/ui/Panel';
import Score from '@/src/components/ui/Score';
import Badge from '@/src/components/Badge';
import EmptyState from '@/src/components/EmptyState';
import ErrorBanner from '@/src/components/ErrorBanner';
import GradingStatusBadge from '@/src/components/student/gradingStatus';
import { statusTone } from '@/src/components/student/TestRunHistory';
import { inputCls } from '@/src/components/ui/tokens';
import { useResource } from '@/src/hooks/useResource';
import { courseAnalyticsClient } from '@/src/clients/CourseAnalyticsClient';
import FlagList, { FlagRules } from './FlagList';
import {
  formatDueRelation,
  formatMinutes,
  stripMarks,
} from '@/src/utils/courseAnalytics';
import type { ActivityEvent, AttemptTimeline, TaskStatus } from 'types/generated';

function formatWhen(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString();
}

const MARK_CLS = (grade: number | null) =>
  grade == null
    ? 'text-faint'
    : grade >= 0.999
      ? 'text-success-text'
      : grade >= 0.5
        ? 'text-warn-text'
        : 'text-danger-text';

/** One assignment's runs (dots, coloured by score) and submissions (ticks) on a shared axis. */
function Strip({
  events,
  start,
  end,
  due,
}: {
  events: ActivityEvent[];
  start: number;
  end: number;
  due: number | null;
}) {
  const marks = stripMarks(events, start, end);
  const span = end - start;
  const dueX = due != null && span > 0 && due >= start && due <= end ? (due - start) / span : null;
  return (
    <svg viewBox="0 0 200 16" className="w-48 h-4" role="img" aria-label="Attempts over time">
      <line x1="0" y1="8" x2="200" y2="8" className="stroke-current text-rule" strokeWidth="1" />
      {dueX != null && (
        <line x1={dueX * 200} y1="0" x2={dueX * 200} y2="16" className="stroke-current text-danger-text" strokeWidth="1" strokeDasharray="2 2" />
      )}
      {marks.map((m, i) =>
        m.kind === 'submission' ? (
          <rect key={i} x={m.x * 196 + 1} y="1" width="2" height="14" className={`fill-current text-accent-text`}>
            <title>{`Submission · ${formatWhen(m.at)}`}</title>
          </rect>
        ) : (
          <circle key={i} cx={m.x * 192 + 4} cy="8" r="3" className={`fill-current ${MARK_CLS(m.grade)}`}>
            <title>{`Test run · ${formatWhen(m.at)} · ${m.grade == null ? 'no score' : `${Math.round(m.grade * 100)}%`}`}</title>
          </circle>
        ),
      )}
    </svg>
  );
}

function TimelineTable({
  timelines,
  events,
  dueAt,
}: {
  timelines: AttemptTimeline[];
  events: ActivityEvent[];
  dueAt: string | null;
}) {
  // Axis spans runs and submissions only; a grading days later would squeeze the attempts.
  const times = events
    .filter((e) => e.kind === 'test_run' || e.kind === 'submission')
    .map((e) => Date.parse(e.at))
    .filter((t) => !Number.isNaN(t));
  const start = times.length ? Math.min(...times) : 0;
  const end = times.length ? Math.max(...times) : 0;
  const due = dueAt ? Date.parse(dueAt) : null;
  const byContent = useMemo(() => {
    const m = new Map<string, ActivityEvent[]>();
    for (const e of events) {
      if (!m.has(e.course_content_id)) m.set(e.course_content_id, []);
      m.get(e.course_content_id)!.push(e);
    }
    return m;
  }, [events]);

  if (timelines.length === 0) {
    return <EmptyState compact title="No test runs or submissions yet." />;
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-canvas border-b border-rule text-xs font-medium text-muted">
            <th className="text-left py-2 px-3">Assignment</th>
            <th className="text-left py-2 px-3">Attempts over time</th>
            <th className="text-right py-2 px-3">Runs</th>
            <th className="text-right py-2 px-3">Submissions</th>
            <th className="text-left py-2 px-3">First / last activity</th>
            <th className="text-left py-2 px-3">Full score reached</th>
            <th className="text-right py-2 px-3">Best / latest</th>
            <th className="text-right py-2 px-3">Days</th>
            <th className="text-right py-2 px-3">Median gap</th>
            <th className="text-right py-2 px-3">Est. active time*</th>
            {dueAt && <th className="text-left py-2 px-3">Last submission</th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-rule-soft">
          {timelines.map((t) => (
            <tr key={t.course_content_id}>
              <td className="py-2 px-3 font-medium text-fg">{t.course_content_title || '—'}</td>
              <td className="py-2 px-3">
                <Strip events={byContent.get(t.course_content_id) ?? []} start={start} end={end} due={due} />
              </td>
              <td className="py-2 px-3 text-right tabular-nums">{t.test_runs ?? 0}</td>
              <td className="py-2 px-3 text-right tabular-nums">{t.submissions ?? 0}</td>
              <td className="py-2 px-3 text-xs text-muted whitespace-nowrap">
                {formatWhen(t.first_activity_at)}
                <br />
                {formatWhen(t.last_activity_at)}
              </td>
              <td className="py-2 px-3 text-xs text-muted whitespace-nowrap">
                {t.first_full_score_at ? formatWhen(t.first_full_score_at) : 'not yet'}
              </td>
              <td className="py-2 px-3 text-right whitespace-nowrap">
                <Score value={t.best_grade} /> <span className="text-subtle">/</span>{' '}
                <Score value={t.latest_grade} />
              </td>
              <td className="py-2 px-3 text-right tabular-nums">{t.active_days ?? 0}</td>
              <td className="py-2 px-3 text-right text-xs text-muted">{formatMinutes(t.median_gap_minutes)}</td>
              <td className="py-2 px-3 text-right text-xs text-muted">{formatMinutes(t.estimated_active_minutes)}</td>
              {dueAt && (
                <td className="py-2 px-3 text-xs text-muted whitespace-nowrap">
                  {formatDueRelation(t.hours_before_due)}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const KIND_LABEL: Record<string, string> = {
  test_run: 'Test run',
  submission: 'Submission',
  grading: 'Grading',
};

function HistoryList({ events }: { events: ActivityEvent[] }) {
  const [content, setContent] = useState('');
  const [kind, setKind] = useState('');
  const assignments = useMemo(() => {
    const m = new Map<string, string>();
    for (const e of events) m.set(e.course_content_id, e.course_content_title || e.course_content_id);
    return [...m.entries()].sort((a, b) => a[1].localeCompare(b[1]));
  }, [events]);
  const rows = events.filter(
    (e) => (!content || e.course_content_id === content) && (!kind || e.kind === kind),
  );

  if (events.length === 0) return <EmptyState compact title="Nothing recorded yet." />;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 print:hidden">
        <select aria-label="Filter by assignment" className={`${inputCls} max-w-xs`} value={content} onChange={(e) => setContent(e.target.value)}>
          <option value="">All assignments</option>
          {assignments.map(([id, title]) => (
            <option key={id} value={id}>{title}</option>
          ))}
        </select>
        <select aria-label="Filter by kind" className={`${inputCls} max-w-xs`} value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">Runs, submissions and feedback</option>
          <option value="test_run">Test runs</option>
          <option value="submission">Submissions</option>
          <option value="grading">Feedback and grades</option>
        </select>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-canvas border-b border-rule text-xs font-medium text-muted">
              <th className="text-left py-2 px-3">When</th>
              <th className="text-left py-2 px-3">Assignment</th>
              <th className="text-left py-2 px-3">Kind</th>
              <th className="text-right py-2 px-3">Result</th>
              <th className="text-left py-2 px-3">Status</th>
              <th className="text-left py-2 px-3">Feedback</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule-soft">
            {rows.map((e, i) => (
              <tr key={`${e.kind}-${e.result_id ?? e.artifact_id ?? ''}-${i}`} className="align-top">
                <td className="py-2 px-3 text-muted whitespace-nowrap">{formatWhen(e.at)}</td>
                <td className="py-2 px-3 text-body">{e.course_content_title || '—'}</td>
                <td className="py-2 px-3">
                  <Badge tone={e.kind === 'grading' ? 'success' : e.kind === 'submission' || e.is_submission ? 'info' : 'muted'}>
                    {e.kind === 'test_run' && e.is_submission ? 'Submission run' : KIND_LABEL[e.kind] ?? e.kind}
                  </Badge>
                </td>
                <td className="py-2 px-3 text-right">
                  {e.kind === 'submission' ? <span className="text-subtle">—</span> : <Score value={e.grade} decimals={1} />}
                </td>
                <td className="py-2 px-3">
                  {e.kind === 'grading' ? (
                    <GradingStatusBadge status={e.status} />
                  ) : e.kind === 'test_run' ? (
                    <Badge tone={statusTone(e.status as TaskStatus | null)}>{e.status ?? 'unknown'}</Badge>
                  ) : null}
                </td>
                <td className="py-2 px-3 max-w-md">
                  {e.feedback && <p className="text-sm text-body whitespace-pre-wrap">{e.feedback}</p>}
                  {e.graded_by && <p className="text-xs text-muted">by {e.graded_by}</p>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * Flags, attempt timeline ("Bearbeitungsverlauf") and full history of one
 * student, all derived from stored test runs, submissions and gradings.
 */
export default function StudentActivity({
  courseMemberId,
  dueAt,
}: {
  courseMemberId: string;
  dueAt: string | null;
}) {
  const { data, loading, error } = useResource(
    () => courseAnalyticsClient.studentActivity(courseMemberId, dueAt),
    [courseMemberId, dueAt],
  );

  if (loading) return <div className="h-40 bg-sunken rounded-lg animate-pulse" />;
  if (error) return <ErrorBanner>{error}</ErrorBanner>;
  if (!data) return null;

  return (
    <>
      <Panel className="space-y-3">
        <h3 className="text-sm font-semibold text-fg">Flags</h3>
        <FlagList flags={data.flags ?? []} />
        <FlagRules rules={data.rules ?? []} />
      </Panel>

      <Panel padding="none">
        <div className="px-4 py-3 border-b border-rule">
          <h3 className="text-sm font-semibold text-fg">Attempt timeline</h3>
          <p className="text-xs text-muted mt-0.5">
            Per assignment, from the timestamps of test runs and submissions. Dots are test runs
            coloured by score, bars are submissions{dueAt ? ', the dashed line is the due date' : ''}.
          </p>
        </div>
        <TimelineTable timelines={data.timelines ?? []} events={data.events ?? []} dueAt={dueAt} />
        <p className="px-4 py-2 text-xs text-subtle border-t border-rule">
          * Estimate: the sum of gaps between consecutive test runs that are at most{' '}
          {data.session_gap_minutes} minutes apart. Work done without running tests is not visible,
          so this is a lower bound, not a measured working time.
        </p>
      </Panel>

      <Panel className="space-y-3">
        <h3 className="text-sm font-semibold text-fg">History of runs, submissions and feedback</h3>
        <HistoryList events={data.events ?? []} />
      </Panel>
    </>
  );
}
