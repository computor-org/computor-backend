'use client';

import type { ReactNode } from 'react';
import Panel from './Panel';
import { TONE_TEXT_CLS, type Tone } from './tones';

/**
 * The summary strip above a list — "12 contents · 4 deployed · 1 failed".
 *
 * Three of these existed: tinted-background tiles with a ring on the grading
 * page, white cards with a coloured number on the lecturer assignments page,
 * and white cards with a grey label on the student assignment detail. They sit
 * two clicks apart and measured the same kind of thing, so this is the one look:
 * a plain panel with the tone carried by the number alone. Tinting the whole
 * tile makes a five-card strip shout louder than the list it is summarising.
 *
 * `href` turns a card into a link — for a count that has somewhere to go.
 */
export function StatCard({
  label,
  value,
  tone = 'muted',
  hint,
}: {
  label: string;
  value: ReactNode;
  /** Colours the number only. Default `muted` renders it as plain body text. */
  tone?: Tone;
  /** Optional second line under the label, e.g. a denominator or a caveat. */
  hint?: string;
}) {
  return (
    <Panel padding="compact">
      <div className={`text-2xl font-bold ${TONE_TEXT_CLS[tone]}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
      {hint && <div className="text-xs text-gray-400 mt-0.5">{hint}</div>}
    </Panel>
  );
}

/**
 * Lays out StatCards. Columns are given rather than derived from the child
 * count: a strip of five that reflows to three then two reads as a deliberate
 * ladder, whereas `auto-fit` picks a different break on every page.
 */
export default function StatGrid({
  columns = 4,
  className = '',
  children,
}: {
  columns?: 3 | 4 | 5;
  className?: string;
  children: ReactNode;
}) {
  const cols = {
    3: 'grid-cols-2 md:grid-cols-3',
    4: 'grid-cols-2 md:grid-cols-4',
    5: 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-5',
  }[columns];

  return <div className={`grid ${cols} gap-4 ${className}`}>{children}</div>;
}
