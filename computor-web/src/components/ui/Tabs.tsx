'use client';

import { ReactNode } from 'react';

/**
 * Shared underline tab bar (the pattern hand-rolled on the course-members Add
 * page). Presentational only: the caller owns the active state, so tabs can be
 * backed by local state or by a `?tab=` query param for deep-linkable pages.
 */
export interface TabDef<Id extends string = string> {
  id: Id;
  label: ReactNode;
}

export default function Tabs<Id extends string>({
  tabs,
  active,
  onSelect,
}: {
  tabs: TabDef<Id>[];
  active: Id;
  onSelect: (id: Id) => void;
}) {
  return (
    <div className="shrink-0 border-b border-gray-200">
      <nav className="flex gap-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => onSelect(tab.id)}
            className={`py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab.id === active
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
