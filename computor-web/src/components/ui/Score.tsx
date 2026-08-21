'use client';

import type { Tone } from './tones';

/**
 * A test result as a percentage, coloured by whether it passed.
 *
 * The backend reports a 0..1 fraction of the tests that passed; every call site
 * was multiplying by 100 itself and picking its own threshold and its own green
 * and red — text-success-text in a tree row, an inline style={{ color: '#10B981' }}
 * on the detail page next to it. One place to decide what "passing" looks like.
 */

/** Fraction at or above which a score reads as a pass. */
export const SCORE_PASS_AT = 0.5;

/** `54.0%`, or an em dash when there is no score. */
export function formatScore(value: number | null | undefined, decimals = 0): string {
  return value == null ? '—' : `${(value * 100).toFixed(decimals)}%`;
}

/**
 * The tone a score reads as, on the same threshold `Score` paints with.
 * For callers that own their own typography — a StatCard's number is set in
 * `text-2xl font-bold`, so it cannot nest a `Score` without the two fighting.
 */
export function scoreTone(value: number | null | undefined, passAt = SCORE_PASS_AT): Tone {
  if (value == null) return 'muted';
  return value >= passAt ? 'success' : 'error';
}

export default function Score({
  /** 0..1 fraction, or null when there is no result yet. */
  value,
  passAt = SCORE_PASS_AT,
  decimals = 0,
  className = '',
}: {
  value: number | null | undefined;
  passAt?: number;
  decimals?: number;
  className?: string;
}) {
  if (value == null) {
    return <span className={`text-sm text-subtle tabular-nums ${className}`}>&mdash;</span>;
  }
  const passing = value >= passAt;
  return (
    <span
      className={`text-sm font-medium tabular-nums ${passing ? 'text-success-text' : 'text-danger-text'} ${className}`}
    >
      {formatScore(value, decimals)}
    </span>
  );
}
