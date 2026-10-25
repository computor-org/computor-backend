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
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { formatDateTime } from '@/src/utils/locale';
import FlagList, { FlagRules } from './FlagList';
import {
  formatDueRelation,
  formatMinutes,
  stripMarks,
} from '@/src/utils/courseAnalytics';
import type { ActivityEvent, AttemptTimeline, TaskStatus } from 'types/generated';

const COPY = {
  de: {
    attemptsLabel: 'Versuche im Zeitverlauf',
    submission: 'Abgabe',
    testRun: 'Testlauf',
    noScore: 'keine Bewertung',
    emptyTimeline: 'Noch keine Testläufe oder Abgaben.',
    assignment: 'Aufgabe',
    attemptsOverTime: 'Versuche im Zeitverlauf',
    runs: 'Läufe',
    submissions: 'Abgaben',
    firstLast: 'Erste / letzte Aktivität',
    fullScore: 'Volle Punktzahl erreicht',
    bestLatest: 'Beste / letzte',
    days: 'Tage',
    medianGap: 'Mediane Pause',
    activeTime: 'Gesch. aktive Zeit*',
    lastSubmission: 'Letzte Abgabe',
    notYet: 'noch nicht',
    kindTestRun: 'Testlauf',
    kindSubmission: 'Abgabe',
    kindGrading: 'Bewertung',
    submissionRun: 'Abgabe-Lauf',
    nothingRecorded: 'Noch nichts erfasst.',
    filterAssignment: 'Nach Aufgabe filtern',
    allAssignments: 'Alle Aufgaben',
    filterKind: 'Nach Art filtern',
    allKinds: 'Läufe, Abgaben und Feedback',
    testRuns: 'Testläufe',
    submissionsKind: 'Abgaben',
    feedbackGrades: 'Feedback und Bewertungen',
    when: 'Wann',
    kind: 'Art',
    result: 'Ergebnis',
    status: 'Status',
    feedback: 'Feedback',
    unknown: 'unbekannt',
    by: (name: string) => `von ${name}`,
    flags: 'Auffälligkeiten',
    timeline: 'Bearbeitungsverlauf',
    timelineHelp: (due: boolean) =>
      `Pro Aufgabe, aus den Zeitstempeln der Testläufe und Abgaben. Punkte sind Testläufe, nach Ergebnis eingefärbt, Balken sind Abgaben${due ? ', die gestrichelte Linie ist die Abgabefrist' : ''}.`,
    estimate: (n: number) =>
      `* Schätzung: Summe der Pausen zwischen aufeinanderfolgenden Testläufen, die höchstens ${n} Minuten auseinanderliegen. Arbeit ohne Testläufe ist nicht sichtbar, daher ist das eine Untergrenze und keine gemessene Arbeitszeit.`,
    history: 'Verlauf der Läufe, Abgaben und Rückmeldungen',
  },
  en: {
    attemptsLabel: 'Attempts over time',
    submission: 'Submission',
    testRun: 'Test run',
    noScore: 'no score',
    emptyTimeline: 'No test runs or submissions yet.',
    assignment: 'Assignment',
    attemptsOverTime: 'Attempts over time',
    runs: 'Runs',
    submissions: 'Submissions',
    firstLast: 'First / last activity',
    fullScore: 'Full score reached',
    bestLatest: 'Best / latest',
    days: 'Days',
    medianGap: 'Median gap',
    activeTime: 'Est. active time*',
    lastSubmission: 'Last submission',
    notYet: 'not yet',
    kindTestRun: 'Test run',
    kindSubmission: 'Submission',
    kindGrading: 'Grading',
    submissionRun: 'Submission run',
    nothingRecorded: 'Nothing recorded yet.',
    filterAssignment: 'Filter by assignment',
    allAssignments: 'All assignments',
    filterKind: 'Filter by kind',
    allKinds: 'Runs, submissions and feedback',
    testRuns: 'Test runs',
    submissionsKind: 'Submissions',
    feedbackGrades: 'Feedback and grades',
    when: 'When',
    kind: 'Kind',
    result: 'Result',
    status: 'Status',
    feedback: 'Feedback',
    unknown: 'unknown',
    by: (name: string) => `by ${name}`,
    flags: 'Flags',
    timeline: 'Attempt timeline',
    timelineHelp: (due: boolean) =>
      `Per assignment, from the timestamps of test runs and submissions. Dots are test runs coloured by score, bars are submissions${due ? ', the dashed line is the due date' : ''}.`,
    estimate: (n: number) =>
      `* Estimate: the sum of gaps between consecutive test runs that are at most ${n} minutes apart. Work done without running tests is not visible, so this is a lower bound, not a measured working time.`,
    history: 'History of runs, submissions and feedback',
  },
};

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
  const language = useUiLanguage();
  const t = COPY[language];
  const marks = stripMarks(events, start, end);
  const span = end - start;
  const dueX = due != null && span > 0 && due >= start && due <= end ? (due - start) / span : null;
  return (
    <svg viewBox="0 0 200 16" className="w-48 h-4" role="img" aria-label={t.attemptsLabel}>
      <line x1="0" y1="8" x2="200" y2="8" className="stroke-current text-rule" strokeWidth="1" />
      {dueX != null && (
        <line x1={dueX * 200} y1="0" x2={dueX * 200} y2="16" className="stroke-current text-danger-text" strokeWidth="1" strokeDasharray="2 2" />
      )}
      {marks.map((m, i) =>
        m.kind === 'submission' ? (
          <rect key={i} x={m.x * 196 + 1} y="1" width="2" height="14" className={`fill-current text-accent-text`}>
            <title>{`${t.submission} · ${formatDateTime(m.at, language)}`}</title>
          </rect>
        ) : (
          <circle key={i} cx={m.x * 192 + 4} cy="8" r="3" className={`fill-current ${MARK_CLS(m.grade)}`}>
            <title>{`${t.testRun} · ${formatDateTime(m.at, language)} · ${m.grade == null ? t.noScore : `${Math.round(m.grade * 100)}%`}`}</title>
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
  const language = useUiLanguage();
  const t = COPY[language];
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
    return <EmptyState compact title={t.emptyTimeline} />;
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-canvas border-b border-rule text-xs font-medium text-muted">
            <th className="text-left py-2 px-3">{t.assignment}</th>
            <th className="text-left py-2 px-3">{t.attemptsOverTime}</th>
            <th className="text-right py-2 px-3">{t.runs}</th>
            <th className="text-right py-2 px-3">{t.submissions}</th>
            <th className="text-left py-2 px-3">{t.firstLast}</th>
            <th className="text-left py-2 px-3">{t.fullScore}</th>
            <th className="text-right py-2 px-3">{t.bestLatest}</th>
            <th className="text-right py-2 px-3">{t.days}</th>
            <th className="text-right py-2 px-3">{t.medianGap}</th>
            <th className="text-right py-2 px-3">{t.activeTime}</th>
            {dueAt && <th className="text-left py-2 px-3">{t.lastSubmission}</th>}
          </tr>
        </thead>
        <tbody className="divide-y divide-rule-soft">
          {timelines.map((tl) => (
            <tr key={tl.course_content_id}>
              <td className="py-2 px-3 font-medium text-fg">{tl.course_content_title || '—'}</td>
              <td className="py-2 px-3">
                <Strip events={byContent.get(tl.course_content_id) ?? []} start={start} end={end} due={due} />
              </td>
              <td className="py-2 px-3 text-right tabular-nums">{tl.test_runs ?? 0}</td>
              <td className="py-2 px-3 text-right tabular-nums">{tl.submissions ?? 0}</td>
              <td className="py-2 px-3 text-xs text-muted whitespace-nowrap">
                {formatDateTime(tl.first_activity_at, language)}
                <br />
                {formatDateTime(tl.last_activity_at, language)}
              </td>
              <td className="py-2 px-3 text-xs text-muted whitespace-nowrap">
                {tl.first_full_score_at ? formatDateTime(tl.first_full_score_at, language) : t.notYet}
              </td>
              <td className="py-2 px-3 text-right whitespace-nowrap">
                <Score value={tl.best_grade} /> <span className="text-subtle">/</span>{' '}
                <Score value={tl.latest_grade} />
              </td>
              <td className="py-2 px-3 text-right tabular-nums">{tl.active_days ?? 0}</td>
              <td className="py-2 px-3 text-right text-xs text-muted">{formatMinutes(tl.median_gap_minutes, language)}</td>
              <td className="py-2 px-3 text-right text-xs text-muted">{formatMinutes(tl.estimated_active_minutes, language)}</td>
              {dueAt && (
                <td className="py-2 px-3 text-xs text-muted whitespace-nowrap">
                  {formatDueRelation(tl.hours_before_due, language)}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function HistoryList({ events }: { events: ActivityEvent[] }) {
  const language = useUiLanguage();
  const t = COPY[language];
  const kindLabel: Record<string, string> = {
    test_run: t.kindTestRun,
    submission: t.kindSubmission,
    grading: t.kindGrading,
  };
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

  if (events.length === 0) return <EmptyState compact title={t.nothingRecorded} />;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 print:hidden">
        <select aria-label={t.filterAssignment} className={`${inputCls} max-w-xs`} value={content} onChange={(e) => setContent(e.target.value)}>
          <option value="">{t.allAssignments}</option>
          {assignments.map(([id, title]) => (
            <option key={id} value={id}>{title}</option>
          ))}
        </select>
        <select aria-label={t.filterKind} className={`${inputCls} max-w-xs`} value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">{t.allKinds}</option>
          <option value="test_run">{t.testRuns}</option>
          <option value="submission">{t.submissionsKind}</option>
          <option value="grading">{t.feedbackGrades}</option>
        </select>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="bg-canvas border-b border-rule text-xs font-medium text-muted">
              <th className="text-left py-2 px-3">{t.when}</th>
              <th className="text-left py-2 px-3">{t.assignment}</th>
              <th className="text-left py-2 px-3">{t.kind}</th>
              <th className="text-right py-2 px-3">{t.result}</th>
              <th className="text-left py-2 px-3">{t.status}</th>
              <th className="text-left py-2 px-3">{t.feedback}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule-soft">
            {rows.map((e, i) => (
              <tr key={`${e.kind}-${e.result_id ?? e.artifact_id ?? ''}-${i}`} className="align-top">
                <td className="py-2 px-3 text-muted whitespace-nowrap">{formatDateTime(e.at, language)}</td>
                <td className="py-2 px-3 text-body">{e.course_content_title || '—'}</td>
                <td className="py-2 px-3">
                  <Badge tone={e.kind === 'grading' ? 'success' : e.kind === 'submission' || e.is_submission ? 'info' : 'muted'}>
                    {e.kind === 'test_run' && e.is_submission ? t.submissionRun : kindLabel[e.kind] ?? e.kind}
                  </Badge>
                </td>
                <td className="py-2 px-3 text-right">
                  {e.kind === 'submission' ? <span className="text-subtle">—</span> : <Score value={e.grade} decimals={1} />}
                </td>
                <td className="py-2 px-3">
                  {e.kind === 'grading' ? (
                    <GradingStatusBadge status={e.status} />
                  ) : e.kind === 'test_run' ? (
                    <Badge tone={statusTone(e.status as TaskStatus | null)}>{e.status ?? t.unknown}</Badge>
                  ) : null}
                </td>
                <td className="py-2 px-3 max-w-md">
                  {e.feedback && <p className="text-sm text-body whitespace-pre-wrap">{e.feedback}</p>}
                  {e.graded_by && <p className="text-xs text-muted">{t.by(e.graded_by)}</p>}
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
  const t = COPY[useUiLanguage()];
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
        <h3 className="text-sm font-semibold text-fg">{t.flags}</h3>
        <FlagList flags={data.flags ?? []} />
        <FlagRules rules={data.rules ?? []} />
      </Panel>

      <Panel padding="none">
        <div className="px-4 py-3 border-b border-rule">
          <h3 className="text-sm font-semibold text-fg">{t.timeline}</h3>
          <p className="text-xs text-muted mt-0.5">
            {t.timelineHelp(Boolean(dueAt))}
          </p>
        </div>
        <TimelineTable timelines={data.timelines ?? []} events={data.events ?? []} dueAt={dueAt} />
        <p className="px-4 py-2 text-xs text-subtle border-t border-rule">
          {t.estimate(data.session_gap_minutes)}
        </p>
      </Panel>

      <Panel className="space-y-3">
        <h3 className="text-sm font-semibold text-fg">{t.history}</h3>
        <HistoryList events={data.events ?? []} />
      </Panel>
    </>
  );
}
