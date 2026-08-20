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
          <dt className="text-gray-500">{item.term}</dt>
          <dd className={item.mono ? 'text-gray-900 font-mono text-xs break-all' : 'text-gray-900'}>
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
