'use client';

import { useMemo, useState } from 'react';
import type { AnalyticsStudentCheckpoint } from '@/src/api/analytics';
import { formatDateTime, formatGrade, formatPercent, formatStudentName, latenessTone } from './format';

type SortKey =
  | 'name'
  | 'submitted_percentage'
  | 'graded_percentage'
  | 'average_grading'
  | 'late_submission_count'
  | 'latest_submission_at';

/** Roster checkpoint table. Click a row to open that student's timeline. */
export default function StudentCheckpointTable({
  students,
  selectedId,
  onSelect,
}: {
  students: AnalyticsStudentCheckpoint[];
  selectedId: string | null;
  onSelect: (student: AnalyticsStudentCheckpoint) => void;
}) {
  const [sortKey, setSortKey] = useState<SortKey>('name');
  const [asc, setAsc] = useState(true);

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
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <Th label="Student" onClick={() => toggle('name')} active={sortKey === 'name'} asc={asc} />
            <Th
              label="Submitted"
              align="right"
              onClick={() => toggle('submitted_percentage')}
              active={sortKey === 'submitted_percentage'}
              asc={asc}
            />
            <Th
              label="Graded"
              align="right"
              onClick={() => toggle('graded_percentage')}
              active={sortKey === 'graded_percentage'}
              asc={asc}
            />
            <Th
              label="Avg grade"
              align="right"
              onClick={() => toggle('average_grading')}
              active={sortKey === 'average_grading'}
              asc={asc}
            />
            <Th
              label="Late"
              align="right"
              onClick={() => toggle('late_submission_count')}
              active={sortKey === 'late_submission_count'}
              asc={asc}
            />
            <Th
              label="Latest submission"
              align="right"
              onClick={() => toggle('latest_submission_at')}
              active={sortKey === 'latest_submission_at'}
              asc={asc}
            />
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {sorted.map((s) => {
            const late = latenessTone(s.late_submission_count ?? 0);
            const selected = s.course_member_id === selectedId;
            return (
              <tr
                key={s.course_member_id}
                onClick={() => onSelect(s)}
                aria-selected={selected}
                className={`cursor-pointer transition-colors ${
                  selected ? 'bg-blue-50' : 'hover:bg-gray-50'
                }`}
              >
                <td className="px-4 py-2.5">
                  <div className="font-medium text-gray-900">{formatStudentName(s)}</div>
                  {s.student_id && (
                    <div className="font-mono text-xs text-gray-400">{s.student_id}</div>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                  {formatPercent(s.submitted_percentage)}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                  {formatPercent(s.graded_percentage)}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-gray-700">
                  {formatGrade(s.average_grading)}
                </td>
                <td className={`px-4 py-2.5 text-right tabular-nums ${late.className}`}>
                  {late.label}
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

function compare(
  a: AnalyticsStudentCheckpoint,
  b: AnalyticsStudentCheckpoint,
  key: SortKey,
): number {
  if (key === 'name') return formatStudentName(a).localeCompare(formatStudentName(b));
  if (key === 'latest_submission_at') {
    return (
      new Date(a.latest_submission_at ?? 0).getTime() -
      new Date(b.latest_submission_at ?? 0).getTime()
    );
  }
  return num(a[key]) - num(b[key]);
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
