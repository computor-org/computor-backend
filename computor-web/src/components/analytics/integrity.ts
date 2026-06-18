/**
 * Academic-integrity model for the lecturer analytics dashboard.
 *
 * The dashboard answers two questions per student: did they pass the work
 * (score, not just submission), and is there reason to look closer (rushed
 * bursts, no-iteration success, tutor concern). These types carry that data;
 * the backend fills them from the analytics snapshot, the demo generator
 * (`demoData.ts`) fills them with synthetic data for local UI testing.
 *
 * Fields are additive over the existing AnalyticsStudentCheckpoint so the page
 * still renders against the current API before the backend aggregations land.
 */

/** Pass bar over standard examples: score must reach this fraction of the
 * possible points. Submitting and scoring 0 is not a pass. */
export const PASS_THRESHOLD = 0.6;

/** Default integrity-flag band: highlight the worst 10% of students per signal. */
export const DEFAULT_FLAG_QUANTILE = 0.1;

export type IntegrityFlagKind = 'velocity' | 'low_iteration' | 'tutor_concern';

export const FLAG_LABEL: Record<IntegrityFlagKind, string> = {
  velocity: 'Burst',
  low_iteration: 'No-iter',
  tutor_concern: 'Tutor',
};

export const FLAG_TITLE: Record<IntegrityFlagKind, string> = {
  velocity: 'Submission burst above this student’s and the cohort’s baseline',
  low_iteration: 'Passed after 0–1 test rounds',
  tutor_concern: 'Tutor comment raised a concern',
};

export interface TutorComment {
  author_role: string;
  text: string;
  created_at: string;
}

/** One standard example for one student: the score-pass row plus the integrity
 * evidence the lecturer judges on. Replaces the old flat event log. */
export interface StandardExampleResult {
  content_id: string;
  path: string;
  title: string;
  category: string;
  /** Best official score as a fraction of the possible points (0..1). */
  score: number | null;
  passed: boolean;
  /** Test runs before the passing/official submission. 0–1 is a flag. */
  test_rounds: number;
  submitted_at: string | null;
  official: boolean;
  late: boolean;
  flags: IntegrityFlagKind[];
  comments: TutorComment[];
  /** Deep link into the example for one-click review. */
  href?: string | null;
}

export interface IntegrityFlagCounts {
  velocity: number;
  low_iteration: number;
  tutor_concern: number;
  total: number;
}

/** Per-student rollup the roster shows for everyone (numbers visible for all),
 * with `worst_band` marking the worst-quantile students for the badge. */
export interface StudentIntegrity {
  standard_passed: number;
  standard_total: number;
  pass_rate: number;
  average_score: number | null;
  flags: IntegrityFlagCounts;
  worst_band: boolean;
}

export function emptyFlagCounts(): IntegrityFlagCounts {
  return { velocity: 0, low_iteration: 0, tutor_concern: 0, total: 0 };
}

/** Roll example-level flags up into per-student counts. */
export function countFlags(examples: StandardExampleResult[]): IntegrityFlagCounts {
  const counts = emptyFlagCounts();
  for (const ex of examples) {
    for (const flag of ex.flags) {
      counts[flag] += 1;
      counts.total += 1;
    }
  }
  return counts;
}

/** Mark the worst `quantile` fraction of students by total flag count. Numbers
 * stay visible for everyone; only the band membership drives the badge. */
export function markWorstBand<T extends { flags: IntegrityFlagCounts }>(
  students: T[],
  quantile: number = DEFAULT_FLAG_QUANTILE,
): Set<number> {
  const ranked = students
    .map((s, i) => ({ i, total: s.flags.total }))
    .filter((r) => r.total > 0)
    .sort((a, b) => b.total - a.total);
  const cut = Math.ceil(students.length * quantile);
  return new Set(ranked.slice(0, cut).map((r) => r.i));
}
