'use client';

import type { ReactNode } from 'react';

/**
 * The control row that sits between a page header and the list it acts on —
 * bulk actions on the left, a search box or status text on the right.
 *
 * Distinct from PageHeader's `actions` slot, which holds the one or two verbs
 * that belong to the *page* (New, Edit, Delete). This holds the ones that belong
 * to the *list* and need to sit next to it: "Release all pending (3)", a filter,
 * a refresh. Hand-rolled today on the lecturer assignments, grading and course
 * members pages, each with its own gap.
 */
export default function Toolbar({
  end,
  className = '',
  children,
}: {
  /** Right-aligned slot — search, a count, a status line. */
  end?: ReactNode;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <div className={`flex flex-wrap items-center gap-3 ${className}`}>
      {children}
      {end != null && <div className="ml-auto flex items-center gap-3">{end}</div>}
    </div>
  );
}
