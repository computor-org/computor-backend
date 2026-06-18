'use client';

import { useMemo, useState } from 'react';
import type { RosterStudent } from '@/src/api/analytics';
import { formatStudentName } from './format';

/**
 * Master list for the analytics dashboard. Names only, alphabetical, with a
 * search box. It deliberately shows NO per-student data (no id, scores, flags,
 * or highlighting): a tutor's screen is glanceable and a passing student must
 * not read another student's standing. Performance and integrity detail live
 * only in the detail view, opened one student at a time.
 */
export default function RosterList({
  students,
  selectedId,
  onSelect,
}: {
  students: RosterStudent[];
  selectedId: string | null;
  onSelect: (student: RosterStudent) => void;
}) {
  const [query, setQuery] = useState('');

  const sorted = useMemo(
    () => [...students].sort((a, b) => formatStudentName(a).localeCompare(formatStudentName(b))),
    [students],
  );
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sorted;
    return sorted.filter((s) => formatStudentName(s).toLowerCase().includes(q));
  }, [sorted, query]);

  if (students.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-gray-300 bg-white p-6 text-center text-sm text-gray-500">
        No students in this snapshot yet. Run an update to import the roster.
      </p>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white" data-testid="analytics-roster">
      <div className="border-b border-gray-100 p-2 print:hidden">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search students"
          aria-label="Search students"
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
        />
      </div>
      <ul className="divide-y divide-gray-100">
        {filtered.map((s) => {
          const selected = s.course_member_id === selectedId;
          return (
            <li key={s.course_member_id}>
              <button
                type="button"
                onClick={() => onSelect(s)}
                aria-current={selected ? 'true' : undefined}
                className={`w-full px-4 py-2 text-left text-sm transition-colors ${
                  selected ? 'bg-blue-50 font-medium text-gray-900' : 'text-gray-800 hover:bg-gray-50'
                }`}
              >
                {formatStudentName(s)}
              </button>
            </li>
          );
        })}
        {filtered.length === 0 && (
          <li className="px-4 py-3 text-sm text-gray-400">No student matches “{query}”.</li>
        )}
      </ul>
    </div>
  );
}
