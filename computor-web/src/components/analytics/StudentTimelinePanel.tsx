'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  AnalyticsApiError,
  getStudentExamples,
  getStudentTimeline,
  type AnalyticsCutoffs,
  type AnalyticsStudentTimeline,
  type AnalyticsTimelineEvent,
  type RosterStudent,
} from '@/src/api/analytics';
import { countFlags, type StandardExampleResult } from './integrity';
import IntegrityBadges from './IntegrityBadges';
import StandardExampleTable from './StandardExampleTable';
import { formatDateTime, formatPercent, formatStudentName } from './format';

/**
 * Per-student evidence. The cumulative curve of official submissions over time,
 * read against the submission cutoff, distinguishes steady work from a
 * last-minute rush. Beneath it, the standard-example table carries the score,
 * pass status, test rounds, flags, and tutor comments the lecturer judges on.
 */
export default function StudentTimelinePanel({
  courseId,
  student,
  cutoffs,
}: {
  courseId: string;
  student: RosterStudent;
  cutoffs: AnalyticsCutoffs;
}) {
  const [timeline, setTimeline] = useState<AnalyticsStudentTimeline | null>(null);
  const [examples, setExamples] = useState<StandardExampleResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setTimeline(null);
      setExamples([]);
      try {
        const [t, ex] = await Promise.all([
          getStudentTimeline(courseId, student.course_member_id, cutoffs),
          getStudentExamples(courseId, student.course_member_id, cutoffs),
        ]);
        if (cancelled) return;
        setTimeline(t);
        setExamples(ex);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof AnalyticsApiError && e.status === 404) {
          setError('No timeline in this snapshot for this student.');
        } else {
          setError(e instanceof Error ? e.message : 'Could not load the timeline.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [courseId, student.course_member_id, cutoffs]);

  const events = useMemo(
    () =>
      [...(timeline?.events ?? [])].sort(
        (a, b) => new Date(a.occurred_at).getTime() - new Date(b.occurred_at).getTime(),
      ),
    [timeline],
  );

  const flags = student.flags ?? countFlags(examples);
  const passText =
    student.standard_passed !== undefined && student.standard_total !== undefined
      ? `${student.standard_passed}/${student.standard_total} standard passed`
      : null;

  return (
    <section
      className="rounded-lg border-2 border-gray-200 bg-white p-5"
      data-testid="analytics-timeline"
      aria-label={`Evidence for ${formatStudentName(student)}`}
    >
      <header className="mb-4 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{formatStudentName(student)}</h3>
          {student.student_id && (
            <p className="font-mono text-xs text-gray-400">{student.student_id}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm">
          {passText && (
            <span className="text-gray-700">
              {passText}{' '}
              <span className="text-gray-400">({formatPercent(student.pass_rate)})</span>
            </span>
          )}
          {student.average_score !== undefined && student.average_score !== null && (
            <span className="text-gray-700">
              avg score{' '}
              <span className="font-medium">{Math.round(student.average_score * 100)}%</span>
            </span>
          )}
          <IntegrityBadges flags={flags} worstBand={student.worst_band} size="md" />
        </div>
      </header>

      {loading && <p className="text-sm text-gray-500">Loading evidence…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && (
        <>
          <CumulativeCurve events={events} cutoff={timeline?.submission_cutoff ?? null} />
          <StandardExampleTable
            examples={examples}
            courseId={courseId}
            courseMemberId={student.course_member_id}
          />
        </>
      )}
    </section>
  );
}

const W = 720;
const H = 200;
const PAD = { top: 16, right: 16, bottom: 28, left: 32 };

/** Step curve of cumulative official submissions, with the cutoff drawn as a
 * vertical guide. Official = events with `submit === true`. */
function CumulativeCurve({
  events,
  cutoff,
}: {
  events: AnalyticsTimelineEvent[];
  cutoff: string | null;
}) {
  const official = events.filter((e) => e.submit === true);

  if (official.length === 0) {
    return (
      <p className="mb-4 rounded-md bg-gray-50 px-3 py-6 text-center text-sm text-gray-500">
        No official submissions to plot.
      </p>
    );
  }

  const times = official.map((e) => new Date(e.occurred_at).getTime());
  const cutoffMs = cutoff ? new Date(cutoff).getTime() : null;
  const minT = Math.min(...times, cutoffMs ?? Infinity);
  const maxT = Math.max(...times, cutoffMs ?? -Infinity);
  const span = Math.max(maxT - minT, 1);
  const total = official.length;

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const x = (t: number) => PAD.left + ((t - minT) / span) * innerW;
  const y = (count: number) => PAD.top + innerH - (count / total) * innerH;

  // Build a step path: horizontal to each event time, then up by one.
  let d = `M ${x(minT).toFixed(1)} ${y(0).toFixed(1)}`;
  let count = 0;
  for (const t of times) {
    d += ` L ${x(t).toFixed(1)} ${y(count).toFixed(1)}`;
    count += 1;
    d += ` L ${x(t).toFixed(1)} ${y(count).toFixed(1)}`;
  }
  d += ` L ${x(maxT).toFixed(1)} ${y(count).toFixed(1)}`;

  const cutoffX = cutoffMs !== null ? x(cutoffMs) : null;

  return (
    <figure className="mb-4">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="block w-full"
        style={{ height: 'auto' }}
        role="img"
        aria-label="Cumulative official submissions over time"
      >
        {/* baseline + 100% gridline */}
        <line x1={PAD.left} y1={y(0)} x2={W - PAD.right} y2={y(0)} stroke="#e5e7eb" />
        <line x1={PAD.left} y1={y(total)} x2={W - PAD.right} y2={y(total)} stroke="#f3f4f6" />
        <text x={4} y={y(total) + 4} className="fill-gray-400 text-[10px]">
          {total}
        </text>
        <text x={4} y={y(0) + 4} className="fill-gray-400 text-[10px]">
          0
        </text>

        {cutoffX !== null && (
          <g>
            <line
              x1={cutoffX}
              y1={PAD.top}
              x2={cutoffX}
              y2={PAD.top + innerH}
              stroke="#f97316"
              strokeDasharray="4 3"
            />
            <text
              x={Math.min(cutoffX + 4, W - PAD.right - 60)}
              y={PAD.top + 10}
              className="fill-orange-500 text-[10px] font-medium"
            >
              cutoff
            </text>
          </g>
        )}

        <path d={d} fill="none" stroke="#2563eb" strokeWidth={2} />
        {/* event dots */}
        {times.map((t, i) => (
          <circle key={i} cx={x(t)} cy={y(i + 1)} r={2.5} fill="#2563eb" />
        ))}

        <text x={PAD.left} y={H - 8} className="fill-gray-400 text-[10px]">
          {formatDateTime(new Date(minT).toISOString())}
        </text>
        <text x={W - PAD.right} y={H - 8} textAnchor="end" className="fill-gray-400 text-[10px]">
          {formatDateTime(new Date(maxT).toISOString())}
        </text>
      </svg>
      <figcaption className="mt-1 text-center text-xs text-gray-400">
        Cumulative official submissions ({total}) against the submission cutoff
      </figcaption>
    </figure>
  );
}
