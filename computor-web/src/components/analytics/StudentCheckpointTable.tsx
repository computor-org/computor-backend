'use client';

import { useMemo, useState } from 'react';
import type { RosterStudent } from '@/src/api/analytics';
import IntegrityBadges from './IntegrityBadges';
import { formatDateTime, formatPercent, formatStudentName, latenessTone } from './format';

type SortKey =
  | 'name'
  | 'pass_rate'
  | 'average_score'
  | 'flags'
  | 'submitted_percentage'
  | 'late_submission_count'
  | 'latest_submission_at';

/** Roster master list. Leads with score-pass over standard examples and the
 * integrity flag counts, the two signals a lecturer triages on. Click a row to
 * open that student's evidence. Sort by flags or pass rate to surface the cases
 * to review first. */
export default function StudentCheckpointTable({
  students,
  selectedId,
  onSelect,
}: {
  students: RosterStudent[];
  selectedId: string | null;
  onSelect: (student: RosterStudent) => void;
}) {
  const [sortKey, setSortKey] = useState<SortKey>('flags');
  const [asc, setAsc] = useState(false);

  const sorted = useMemo(() => {
    const factor = asc ? 1 : -1;
    return [...students].sort((a, b) => factor * compare(a, b, sortKey));
  }, [students, sortKey, asc]);

  const toggle = (key: SortKey) => {
    if (key === sortKey) setAsc((v) => !v);
    else {
      setSortKey(key);
      setAsc(key === 'name');
    }
  };

  if (students.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-gray-300 bg-white p-6 text-center text-sm text-gray-500">
        No students in this snapshot yet. Run an update to import the roster.
      </p>
    );
  }

  return (
    <div
      className="overflow-x-auto rounded-lg border border-gray-200 bg-white"
      data-testid="analytics-roster"
    >
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <Th label="Student" onClick={() => toggle('name')} active={sortKey === 'name'} asc={asc} />
            <Th label="Passed" align="right" onClick={() => toggle('pass_rate')} active={sortKey === 'pass_rate'} asc={asc} />
            <Th label="Avg score" align="right" onClick={() => toggle('average_score')} active={sortKey === 'average_score'} asc={asc} />
            <Th label="Flags" onClick={() => toggle('flags')} active={sortKey === 'flags'} asc={asc} />
            <Th label="Submitted" align="right" onClick={() => toggle('submitted_percentage')} active={sortKey === 'submitted_percentage'} asc={asc} />
            <Th label="Latest" align="right" onClick={() => toggle('latest_submission_at')} active={sortKey === 'latest_submission_at'} asc={asc} />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {sorted.map((s) => {
            const selected = s.course_member_id === selectedId;
            const passText =
              s.standard_passed !== undefined && s.standard_total !== undefined
                ? `${s.standard_passed}/${s.standard_total}`
                : '—';
            const late = latenessTone(s.late_submission_count ?? 0);
            return (
              <tr
                key={s.course_member_id}
                onClick={() => onSelect(s)}
                aria-selected={selected}
                className={`cursor-pointer transition-colors ${
                  selected ? 'bg-blue-50' : s.worst_band ? 'bg-rose-50/40 hover:bg-rose-50' : 'hover:bg-gray-50'
                }`}
              >
                <td className="px-4 py-2.5">
                  <div className="font-medium text-gray-900">{formatStudentName(s)}</div>
                  {s.student_id && (
                    <div className="font-mono text-xs text-gray-400">{s.student_id}</div>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  <span className="text-gray-900">{passText}</span>
                  {s.pass_rate !== undefined && (
                    <span className="ml-1 text-xs text-gray-400">{formatPercent(s.pass_rate)}</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                  {s.average_score === undefined || s.average_score === null
                    ? '—'
                    : `${Math.round(s.average_score * 100)}%`}
                </td>
                <td className="px-4 py-2.5">
                  <IntegrityBadges flags={s.flags} worstBand={s.worst_band} />
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-500">
                  {formatPercent(s.submitted_percentage)}
                  {(s.late_submission_count ?? 0) > 0 && (
                    <span className={`ml-1 text-xs ${late.className}`}>{late.label}</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right text-xs text-gray-500">
                  {formatDateTime(s.latest_submission_at)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function compare(a: RosterStudent, b: RosterStudent, key: SortKey): number {
  if (key === 'name') return formatStudentName(a).localeCompare(formatStudentName(b));
  if (key === 'flags') return num(a.flags?.total) - num(b.flags?.total);
  if (key === 'pass_rate') return num(a.pass_rate) - num(b.pass_rate);
  if (key === 'average_score') return num(a.average_score) - num(b.average_score);
  if (key === 'latest_submission_at') {
    return (
      new Date(a.latest_submission_at ?? 0).getTime() -
      new Date(b.latest_submission_at ?? 0).getTime()
    );
  }
  return num(a[key as 'submitted_percentage' | 'late_submission_count']) -
    num(b[key as 'submitted_percentage' | 'late_submission_count']);
}

function num(v: number | null | undefined): number {
  return v ?? -1;
}

function Th({
  label,
  align = 'left',
  onClick,
  active,
  asc,
}: {
  label: string;
  align?: 'left' | 'right';
  onClick: () => void;
  active: boolean;
  asc: boolean;
}) {
  return (
    <th
      scope="col"
      className={`px-4 py-2 text-${align} text-xs font-semibold uppercase tracking-wide text-gray-500`}
    >
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center gap-1 hover:text-gray-900"
      >
        {label}
        <span className={`text-[10px] ${active ? 'text-gray-700' : 'text-transparent'}`}>
          {asc ? '▲' : '▼'}
        </span>
      </button>
    </th>
  );
}
