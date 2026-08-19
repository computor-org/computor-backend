// Rendering for the per-assignment test-run and submission budgets.
//
// The limit is resolved server-side (submission group override → course
// content → course default), so the client only decides how to show it. The
// rule that matters: render the denominator whenever a limit exists, even at
// zero usage — a student needs to see "0 / 2" before they start, not only
// after their first run.

/** A usage counter against its cap: `0 / 2`, or a bare `3` when uncapped. */
export const formatUsage = (
  used: number | null | undefined,
  max: number | null | undefined,
): string => {
  const count = used ?? 0;
  return max == null ? String(count) : `${count} / ${max}`;
};

/** Compact form for dense rows (tables, trees): `0/2`. */
export const formatUsageCompact = (
  used: number | null | undefined,
  max: number | null | undefined,
): string => {
  const count = used ?? 0;
  return max == null ? String(count) : `${count}/${max}`;
};

/** Short label for a cap on its own, e.g. in a lecturer-facing badge. */
export const formatLimit = (max: number | null | undefined): string =>
  max == null ? 'unlimited' : String(max);
