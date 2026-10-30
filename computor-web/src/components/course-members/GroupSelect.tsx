'use client';

import type { CourseGroupList } from 'types/generated';
import { useUiLanguage } from '@/src/hooks/useUiLanguage';
import { courseGroupTitle } from '@/src/utils/courseGroups';

const CELL_CLS =
  'px-2 py-1 border border-rule-strong rounded-lg text-sm focus:ring-2 focus:ring-accent-line focus:border-transparent disabled:opacity-50';

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
  const de = useUiLanguage() === 'de';
  return (
    <select
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      className={className}
    >
      <option value="">{de ? '— keine Gruppe —' : '— no group —'}</option>
      {groups.map((g) => (
        <option key={g.id} value={g.id}>
          {courseGroupTitle(g.title, de ? 'de' : 'en') || g.id}
        </option>
      ))}
    </select>
  );
}
