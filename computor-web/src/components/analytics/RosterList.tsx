'use client';

import { useMemo, useRef } from 'react';
import type { KeyboardEvent } from 'react';
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
  query,
  onQueryChange,
  onSelect,
}: {
  students: RosterStudent[];
  selectedId: string | null;
  query: string;
  onQueryChange: (query: string) => void;
  onSelect: (student: RosterStudent) => void;
}) {
  const buttonRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const sorted = useMemo(
    () => [...students].sort((a, b) => formatStudentName(a).localeCompare(formatStudentName(b))),
    [students],
  );
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sorted;
    return sorted.filter((s) => formatStudentName(s).toLowerCase().includes(q));
  }, [sorted, query]);

  const focusStudent = (index: number) => {
    buttonRefs.current[index]?.focus();
  };

  const handleSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== 'ArrowDown' || filtered.length === 0) return;

    event.preventDefault();
    focusStudent(0);
  };

  const handleStudentKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (filtered.length === 0) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      focusStudent(Math.min(index + 1, filtered.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      focusStudent(Math.max(index - 1, 0));
    } else if (event.key === 'Home') {
      event.preventDefault();
      focusStudent(0);
    } else if (event.key === 'End') {
      event.preventDefault();
      focusStudent(filtered.length - 1);
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
    <div className="rounded-lg border border-gray-200 bg-white" data-testid="analytics-roster">
      <div className="border-b border-gray-100 p-2 print:hidden">
        <input
          type="search"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={handleSearchKeyDown}
          placeholder="Search students"
          aria-label="Search students"
          className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
        />
      </div>
      <ul className="divide-y divide-gray-100">
        {filtered.map((s, index) => {
          const selected = s.course_member_id === selectedId;
          return (
            <li key={s.course_member_id}>
              <button
                ref={(element) => {
                  buttonRefs.current[index] = element;
                }}
                type="button"
                onClick={() => onSelect(s)}
                onKeyDown={(event) => handleStudentKeyDown(event, index)}
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
          <li className="px-4 py-3 text-sm text-gray-400">No students match “{query}”.</li>
        )}
      </ul>
    </div>
  );
}
