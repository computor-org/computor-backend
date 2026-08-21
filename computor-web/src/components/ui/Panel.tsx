'use client';

import type { ReactNode } from 'react';

/**
 * The app's one white card: surface, border, radius, padding.
 *
 * Pages had been spelling this out inline — `bg-surface border border-rule
 * rounded-lg p-6` — which is how the same card ended up at p-4, p-5, p-6 and p-8
 * on neighbouring pages. Callers choose a *density*, never a padding value, so
 * there is nothing left to disagree about.
 *
 * `<SectionCard>` is this plus a heading; reach for that when the panel has a
 * title, and for this when it doesn't.
 */
export type PanelPadding = 'default' | 'compact' | 'none';

const PADDING_CLS: Record<PanelPadding, string> = {
  default: 'p-6',
  compact: 'p-4',
  // For a panel whose children own the padding — a table, or a header strip
  // above a list, where an outer pad would double up on the inner one.
  none: '',
};

export default function Panel({
  padding = 'default',
  className = '',
  children,
}: {
  padding?: PanelPadding;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={`bg-surface border border-rule rounded-lg ${PADDING_CLS[padding]} ${className}`}>
      {children}
    </div>
  );
}

/**
 * A panel whose body is a list of rows, separated rather than padded — the
 * "stack of links" card used by the organization, course-family and example
 * detail pages. Rows supply their own `px-4 py-3`.
 */
export function PanelList({ className = '', children }: { className?: string; children: ReactNode }) {
  return (
    <Panel padding="none" className={`divide-y divide-rule-soft ${className}`}>
      {children}
    </Panel>
  );
}
