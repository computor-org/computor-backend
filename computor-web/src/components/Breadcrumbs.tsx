'use client';

import Link from 'next/link';
import { Fragment } from 'react';

export interface Crumb {
  label: string;
  href?: string;
}

/**
 * Entity-centric breadcrumb trail rendered at the top of a panel page.
 *
 * Pages pass explicit items with already-resolved labels (the real entity
 * name, never a raw id or endpoint noun), e.g.
 *   [{label:'Examples', href:'/examples'}, {label:'Quadratic Equation'}]
 * The last item is the current page (not a link).
 */
export default function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-4">
      <ol className="flex flex-wrap items-center gap-1.5 text-sm text-gray-500">
        {items.map((item, i) => {
          const last = i === items.length - 1;
          return (
            <Fragment key={i}>
              {i > 0 && (
                <li aria-hidden="true" className="text-gray-300 select-none">
                  /
                </li>
              )}
              <li className="min-w-0">
                {item.href && !last ? (
                  <Link href={item.href} className="hover:text-blue-600 transition-colors">
                    {item.label}
                  </Link>
                ) : (
                  <span className={last ? 'font-medium text-gray-900' : ''} aria-current={last ? 'page' : undefined}>
                    {item.label}
                  </span>
                )}
              </li>
            </Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
