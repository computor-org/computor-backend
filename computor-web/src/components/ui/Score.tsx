'use client';

/**
 * A test result as a percentage, coloured by whether it passed.
 *
 * The backend reports a 0..1 fraction of the tests that passed; every call site
 * was multiplying by 100 itself and picking its own threshold and its own green
 * and red — text-green-600 in a tree row, an inline style={{ color: '#10B981' }}
 * on the detail page next to it. One place to decide what "passing" looks like.
 */
export default function Score({
  /** 0..1 fraction, or null when there is no result yet. */
  value,
  /** Fraction at or above which the result reads as a pass. */
  passAt = 0.5,
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
      className={`text-sm font-medium tabular-nums ${passing ? 'text-green-600' : 'text-red-600'} ${className}`}
    >
      {(value * 100).toFixed(decimals)}%
    </span>
  );
}
