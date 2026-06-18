'use client';

import {
  FLAG_LABEL,
  FLAG_TITLE,
  PASS_THRESHOLD,
  groupByUnit,
  type StandardExampleResult,
  type UnitGroup,
} from './integrity';
import { formatDateTime } from './format';

/**
 * Per-example evidence for one student, grouped by week/unit with per-unit
 * subtotals: the score-pass row plus the integrity signals (test rounds,
 * lateness, flags) and tutor comments. This is what a lecturer judges on, so it
 * replaces the old flat event log. Clicking an example opens its source code in
 * a modal over the page, so the student detail is never lost.
 */
export default function StandardExampleTable({
  examples,
  onOpenExample,
}: {
  examples: StandardExampleResult[];
  onOpenExample: (example: StandardExampleResult) => void;
}) {
  if (examples.length === 0) {
    return <p className="text-sm text-gray-500">No standard examples in this snapshot.</p>;
  }
  const units = groupByUnit(examples);
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr className="text-xs font-semibold uppercase tracking-wide text-gray-500">
            <th className="px-3 py-2 text-left">Example</th>
            <th className="px-3 py-2 text-right">Score</th>
            <th className="px-3 py-2 text-center">Pass</th>
            <th className="px-3 py-2 text-right" title="Test runs before the passing submission">
              Rounds
            </th>
            <th className="px-3 py-2 text-right">Submitted</th>
            <th className="px-3 py-2 text-left">Flags</th>
          </tr>
        </thead>
        {units.map((unit) => (
          <tbody key={unit.key} className="divide-y divide-gray-100">
            <UnitHeader unit={unit} />
            {unit.examples.map((ex) => (
              <ExampleRow key={ex.content_id} ex={ex} onOpen={onOpenExample} />
            ))}
          </tbody>
        ))}
      </table>
    </div>
  );
}

/** Per-unit subtotal banner: passed/attempted, average score, flag count. */
function UnitHeader({ unit }: { unit: UnitGroup }) {
  const avg = unit.averageScore === null ? null : Math.round(unit.averageScore * 100);
  return (
    <tr className="bg-gray-100/70">
      <th scope="rowgroup" className="px-3 py-1.5 text-left text-sm font-semibold text-gray-700">
        {unit.label}
      </th>
      <td className="px-3 py-1.5 text-right text-xs text-gray-500">{avg === null ? '' : `${avg}%`}</td>
      <td className="px-3 py-1.5 text-center text-xs font-medium text-gray-600" title="passed / attempted">
        {unit.passed}/{unit.total}
      </td>
      <td />
      <td />
      <td className="px-3 py-1.5 text-left text-xs text-gray-500">
        {unit.flagTotal > 0 ? `${unit.flagTotal} flag${unit.flagTotal === 1 ? '' : 's'}` : ''}
      </td>
    </tr>
  );
}

function ExampleRow({
  ex,
  onOpen,
}: {
  ex: StandardExampleResult;
  onOpen: (example: StandardExampleResult) => void;
}) {
  const scorePct = ex.score === null ? null : Math.round(ex.score * 100);
  return (
    <>
      <tr className={ex.flags.length ? 'bg-rose-50/40' : undefined}>
        <td className="px-3 py-2">
          <button
            type="button"
            onClick={() => onOpen(ex)}
            className="text-left font-medium text-blue-600 hover:underline"
            title="View source code"
          >
            {ex.title}
          </button>
          <div className="font-mono text-[11px] text-gray-400">{ex.path}</div>
        </td>
        <td className="px-3 py-2 text-right tabular-nums">
          {scorePct === null ? (
            <span className="text-gray-300">—</span>
          ) : (
            <span className={scorePct >= PASS_THRESHOLD * 100 ? 'text-gray-800' : 'text-rose-600'}>
              {scorePct}%
            </span>
          )}
        </td>
        <td className="px-3 py-2 text-center">
          {ex.submitted_at === null ? (
            <span className="text-gray-300">—</span>
          ) : ex.passed ? (
            <span className="text-emerald-600" title={`>= ${PASS_THRESHOLD * 100}%`}>
              ✓
            </span>
          ) : (
            <span className="text-rose-500">✗</span>
          )}
        </td>
        <td className="px-3 py-2 text-right tabular-nums text-gray-600">
          {ex.submitted_at === null ? '—' : ex.test_rounds}
        </td>
        <td className="px-3 py-2 text-right text-xs text-gray-500">
          {formatDateTime(ex.submitted_at)}
          {ex.late && <span className="ml-1 text-orange-500" title="After submission cutoff">late</span>}
        </td>
        <td className="px-3 py-2">
          <span className="inline-flex flex-wrap gap-1">
            {ex.flags.map((f) => (
              <span
                key={f}
                title={FLAG_TITLE[f]}
                className="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-medium text-rose-700"
              >
                {FLAG_LABEL[f]}
              </span>
            ))}
          </span>
        </td>
      </tr>
      {ex.comments.map((c, i) => (
        <tr key={`${ex.content_id}-c${i}`} className="bg-gray-50/60">
          <td />
          <td colSpan={5} className="px-3 pb-2 text-xs text-gray-600">
            <span className="font-medium text-gray-500">{c.author_role}:</span> {c.text}{' '}
            <span className="text-gray-400">({formatDateTime(c.created_at)})</span>
          </td>
        </tr>
      ))}
    </>
  );
}
