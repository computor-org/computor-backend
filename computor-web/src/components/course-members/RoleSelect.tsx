'use client';

import { courseRoleLabel } from '@/src/utils/courseRoles';

const CELL_CLS =
  'px-2 py-1 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent disabled:opacity-50';

/** Course-role `<select>` used across the add-members flows. */
export default function RoleSelect({
  value,
  onChange,
  options,
  disabled,
  className = CELL_CLS,
}: {
  value: string;
  onChange: (value: string) => void;
  options: readonly string[];
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
      {options.map((r) => (
        <option key={r} value={r}>
          {courseRoleLabel(r)}
        </option>
      ))}
    </select>
  );
}
