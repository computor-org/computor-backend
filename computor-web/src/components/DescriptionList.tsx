'use client';

import { ReactNode } from 'react';

/** Read-only term/value grid, as used for locked settings. */
export default function DescriptionList({
  items,
}: {
  items: { term: string; value: ReactNode; mono?: boolean }[];
}) {
  return (
    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
      {items.map((item) => (
        <div key={item.term}>
          <dt className="text-muted">{item.term}</dt>
          <dd className={item.mono ? 'text-fg font-mono text-xs break-all' : 'text-fg'}>
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
