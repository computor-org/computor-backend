'use client';

import type { CourseGroupList } from 'types/generated';

const CELL_CLS =
  'px-2 py-1 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50';

/** Course-group `<select>` (with a "no group" option) for the user-list flow. */
export default function GroupSelect({
  value,
  onChange,
  groups,
  disabled,
  className = CELL_CLS,
}: {
  value: string;
  onChange: (value: string) => void;
  groups: CourseGroupList[];
  disabled?: boolean;
  className?: string;
}) {
  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      className={className}
    >
      <option value="">— no group —</option>
      {groups.map((g) => (
        <option key={g.id} value={g.id}>
          {g.title || g.id}
        </option>
      ))}
    </select>
  );
}
