'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  AnalyticsApiError,
  getStudentTimeline,
  type AnalyticsCutoffs,
  type AnalyticsStudentCheckpoint,
  type AnalyticsStudentTimeline,
  type AnalyticsTimelineEvent,
} from '@/src/api/analytics';
import { cutoffRelationTone, formatDateTime, formatGrade, formatStudentName } from './format';

/**
 * Per-student evidence. The cumulative curve of official submissions over time,
 * read against the submission cutoff, is the one view that distinguishes steady
 * work from a last-minute rush — so it is the panel's hero. Everything else is a
 * plain event log beneath it.
 */
export default function StudentTimelinePanel({
  courseId,
  student,
  cutoffs,
}: {
  courseId: string;
  student: AnalyticsStudentCheckpoint;
  cutoffs: AnalyticsCutoffs;
}) {
  const [timeline, setTimeline] = useState<AnalyticsStudentTimeline | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setTimeline(null);
      try {
        const t = await getStudentTimeline(courseId, student.course_member_id, cutoffs);
        if (!cancelled) setTimeline(t);
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

  return (
    <section
      className="rounded-lg border-2 border-gray-200 bg-white p-5"
      data-testid="analytics-timeline"
      aria-label={`Timeline for ${formatStudentName(student)}`}
    >
      <header className="mb-4 flex items-baseline justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{formatStudentName(student)}</h3>
          {student.student_id && (
            <p className="font-mono text-xs text-gray-400">{student.student_id}</p>
          )}
        </div>
        <p className="text-xs text-gray-500">
          {events.length} event{events.length === 1 ? '' : 's'}
        </p>
      </header>

      {loading && <p className="text-sm text-gray-500">Loading timeline…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && (
        <>
          <CumulativeCurve events={events} cutoff={timeline?.submission_cutoff ?? null} />
          <EventLog events={events} />
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
        className="h-48 w-full"
        role="img"
        aria-label="Cumulative official submissions over time"
        preserveAspectRatio="none"
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

function EventLog({ events }: { events: AnalyticsTimelineEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-gray-500">No events recorded.</p>;
  }
  return (
    <ol className="divide-y divide-gray-100">
      {events.map((e, i) => {
        const tone = cutoffRelationTone(e.relation_to_submission_cutoff);
        return (
          <li key={`${e.occurred_at}-${i}`} className="flex items-center gap-3 py-2 text-sm">
            <span className={`h-2 w-2 shrink-0 rounded-full ${tone.dot}`} aria-hidden />
            <span className="w-36 shrink-0 text-xs text-gray-500">{formatDateTime(e.occurred_at)}</span>
            <span className="flex-1 truncate text-gray-800">
              {e.title || e.path || e.event_type}
              {e.submit === true && (
                <span className="ml-2 rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">
                  official
                </span>
              )}
            </span>
            {e.grade !== null && e.grade !== undefined && (
              <span className="shrink-0 tabular-nums text-gray-600">{formatGrade(e.grade)}</span>
            )}
            {tone.label && <span className="shrink-0 text-xs text-gray-400">{tone.label}</span>}
          </li>
        );
      })}
    </ol>
  );
}
