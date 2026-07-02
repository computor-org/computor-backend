'use client';

/**
 * Cumulative submission curve — a step curve of how many assignments the
 * student had officially submitted over time, windowed to an optional start
 * date and with a configurable due date drawn as a vertical guide. Dots after
 * the due date are marked late (red).
 *
 * Ported from the retired analytics dashboard, but here it runs off the grading
 * data already loaded (each submittable node's latest official submission), so
 * it needs no snapshot and no extra request.
 */

type CurvePoint = { at: string; label?: string | null };

const W = 720;
const H = 200;
const PAD = { top: 16, right: 16, bottom: 28, left: 32 };

function fmt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function SubmissionCurve({
  points,
  total,
  startDate,
  dueDate,
}: {
  points: CurvePoint[];
  total: number;
  startDate: string | null;
  dueDate: string | null;
}) {
  const startMs = startDate ? new Date(startDate).getTime() : NaN;
  const startValid = !Number.isNaN(startMs);
  const dueMs = dueDate ? new Date(dueDate).getTime() : NaN;
  const dueValid = !Number.isNaN(dueMs);

  // Sort, then window to submissions on/after the start date.
  const windowed = [...points]
    .filter((p) => p.at && !Number.isNaN(new Date(p.at).getTime()))
    .filter((p) => !startValid || new Date(p.at).getTime() >= startMs)
    .sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());

  if (windowed.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-2">Submission timeline</h3>
        <p className="rounded-md bg-gray-50 px-3 py-6 text-center text-sm text-gray-500">
          {startValid ? 'No official submissions in the selected window.' : 'No official submissions to plot.'}
        </p>
      </div>
    );
  }

  const times = windowed.map((p) => new Date(p.at).getTime());
  // Axis begins at the start date (when set), else the first submission.
  const minT = Math.min(...times, startValid ? startMs : Infinity, dueValid ? dueMs : Infinity);
  const maxT = Math.max(...times, dueValid ? dueMs : -Infinity);
  const span = Math.max(maxT - minT, 1);
  const denom = Math.max(total, windowed.length, 1);

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const x = (t: number) => PAD.left + ((t - minT) / span) * innerW;
  const y = (count: number) => PAD.top + innerH - (count / denom) * innerH;

  // Step path: horizontal to each submission time, then up by one.
  let d = `M ${x(minT).toFixed(1)} ${y(0).toFixed(1)}`;
  let count = 0;
  for (const t of times) {
    d += ` L ${x(t).toFixed(1)} ${y(count).toFixed(1)}`;
    count += 1;
    d += ` L ${x(t).toFixed(1)} ${y(count).toFixed(1)}`;
  }
  d += ` L ${x(maxT).toFixed(1)} ${y(count).toFixed(1)}`;

  const dueX = dueValid ? x(dueMs) : null;
  const lateCount = dueValid ? times.filter((t) => t > dueMs).length : 0;

  return (
    <figure className="bg-white rounded-lg border border-gray-200 p-5 m-0">
      <figcaption className="text-sm font-semibold text-gray-900 mb-3">
        Submission timeline
      </figcaption>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="block w-full"
        style={{ height: 'auto' }}
        role="img"
        aria-label="Cumulative official submissions over time"
      >
        {/* baseline + top gridline */}
        <line x1={PAD.left} y1={y(0)} x2={W - PAD.right} y2={y(0)} stroke="#e5e7eb" />
        <line x1={PAD.left} y1={y(denom)} x2={W - PAD.right} y2={y(denom)} stroke="#f3f4f6" />
        <text x={4} y={y(denom) + 4} className="fill-gray-400 text-[10px]">
          {denom}
        </text>
        <text x={4} y={y(0) + 4} className="fill-gray-400 text-[10px]">
          0
        </text>

        {dueX !== null && (
          <g>
            <line
              x1={dueX}
              y1={PAD.top}
              x2={dueX}
              y2={PAD.top + innerH}
              stroke="#f97316"
              strokeDasharray="4 3"
            />
            <text
              x={Math.min(dueX + 4, W - PAD.right - 40)}
              y={PAD.top + 10}
              className="fill-orange-500 text-[10px] font-medium"
            >
              due
            </text>
          </g>
        )}

        <path d={d} fill="none" stroke="#2563eb" strokeWidth={2} />
        {/* submission dots — red when after the due date */}
        {times.map((t, i) => (
          <circle
            key={i}
            cx={x(t)}
            cy={y(i + 1)}
            r={2.5}
            fill={dueValid && t > dueMs ? '#ef4444' : '#2563eb'}
          />
        ))}

        <text x={PAD.left} y={H - 8} className="fill-gray-400 text-[10px]">
          {fmt(new Date(minT).toISOString())}
        </text>
        <text
          x={W - PAD.right}
          y={H - 8}
          textAnchor="end"
          className="fill-gray-400 text-[10px]"
        >
          {fmt(new Date(maxT).toISOString())}
        </text>
      </svg>
      <figcaption className="mt-2 text-center text-xs text-gray-400">
        Cumulative assignments submitted ({windowed.length}/{total})
        {startValid && <span> · from start date</span>}
        {dueValid && lateCount > 0 && (
          <span className="text-red-500"> · {lateCount} after due date</span>
        )}
      </figcaption>
    </figure>
  );
}
