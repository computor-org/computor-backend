/**
 * Synthetic analytics dataset for local UI testing without a backend or real
 * course data. Enabled by NEXT_PUBLIC_ANALYTICS_DEMO=1 (see `src/api/analytics`).
 *
 * Deterministic: a seeded PRNG so the same students/curves render every run,
 * which makes the dashboard reviewable and screenshot-stable. No real student
 * data ever lives here; the distributions are hand-tuned to exercise every
 * roster column, flag, and detail panel.
 */

import type {
  AnalyticsCourseSummary,
  AnalyticsStudentCheckpoint,
  AnalyticsStudentTimeline,
  AnalyticsTimelineEvent,
} from '@/src/generated/types/analytics';
import {
  PASS_THRESHOLD,
  countFlags,
  markWorstBand,
  type ExampleSource,
  type IntegrityFlagKind,
  type StandardExampleResult,
  type StudentIntegrity,
  type TutorComment,
} from './integrity';

export const DEMO_COURSE_ID = '11111111-1111-1111-1111-111111111111';
export const DEMO_SUBMISSION_CUTOFF = '2026-06-18T22:01:00.000Z';

export type DemoStudent = AnalyticsStudentCheckpoint & StudentIntegrity;

export interface DemoStudentDetail {
  timeline: AnalyticsStudentTimeline;
  examples: StandardExampleResult[];
}

/** mulberry32: tiny deterministic PRNG so the demo is stable across reloads. */
function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const FIRST = ['Ada', 'Grace', 'Alan', 'Edsger', 'Donald', 'Barbara', 'Ken', 'Dennis',
  'Linus', 'Margaret', 'John', 'Katherine', 'Tim', 'Radia', 'Leslie', 'Guido',
  'Bjarne', 'James', 'Anita', 'Frances', 'Vint', 'Shafi', 'Andrew', 'Sophie',
  'Niklaus', 'Hedy', 'Claude', 'Emmy', 'Carl', 'Joan', 'Per', 'Maryam',
  'Ingrid', 'Terence', 'Daniel', 'Karen'];
const LAST = ['Lovelace', 'Hopper', 'Turing', 'Dijkstra', 'Knuth', 'Liskov', 'Thompson',
  'Ritchie', 'Torvalds', 'Hamilton', 'McCarthy', 'Johnson', 'Berners-Lee',
  'Perlman', 'Lamport', 'van Rossum', 'Stroustrup', 'Gosling', 'Borg', 'Allen',
  'Cerf', 'Goldwasser', 'Yao', 'Wilson', 'Wirth', 'Lamarr', 'Shannon',
  'Noether', 'Gauss', 'Clarke', 'Enflo', 'Mirzakhani', 'Daubechies', 'Tao',
  'Bernoulli', 'Sparck'];

const N_STANDARD = 12;
const STUDENT_COUNT = 36;

/** Three behavioural archetypes drive the spread the lecturer needs to see. */
type Profile = 'steady' | 'struggling' | 'rusher';

function profileFor(r: () => number): Profile {
  const x = r();
  if (x < 0.55) return 'steady';
  if (x < 0.8) return 'struggling';
  return 'rusher';
}

function exampleTitle(i: number): { path: string; title: string } {
  const week = Math.floor(i / 3) + 1;
  const n = (i % 3) + 1;
  return { path: `week_${week}.example_${n}`, title: `Week ${week} · Example ${n}` };
}

function makeExamples(seed: number, profile: Profile, cutoffMs: number): StandardExampleResult[] {
  const r = rng(seed);
  const examples: StandardExampleResult[] = [];
  // Rushers compress submissions into the final ~18h before the cutoff.
  const rushStart = cutoffMs - 18 * 3600 * 1000;
  const termStart = cutoffMs - 12 * 24 * 3600 * 1000;

  for (let i = 0; i < N_STANDARD; i += 1) {
    const { path, title } = exampleTitle(i);
    const attempted = profile === 'struggling' ? r() < 0.78 : r() < 0.95;
    if (!attempted) {
      examples.push({
        content_id: `c-${seed}-${i}`,
        path,
        title,
        category: 'standard',
        score: null,
        passed: false,
        test_rounds: 0,
        submitted_at: null,
        official: false,
        late: false,
        flags: [],
        comments: [],
        href: `/courses/${DEMO_COURSE_ID}/contents/c-${seed}-${i}`,
      });
      continue;
    }

    const base = profile === 'struggling' ? 0.35 : profile === 'rusher' ? 0.7 : 0.78;
    const score = clamp(base + (r() - 0.5) * 0.5, 0, 1);
    const passed = score >= PASS_THRESHOLD;

    const submittedMs = profile === 'rusher'
      ? rushStart + r() * (cutoffMs - rushStart) + (r() < 0.25 ? r() * 6 * 3600 * 1000 : 0)
      : termStart + r() * (cutoffMs - termStart);
    const late = submittedMs > cutoffMs;

    // Rushers and some lucky passes show 0–1 test rounds before success.
    const rounds = profile === 'rusher'
      ? Math.floor(r() * 2)
      : profile === 'struggling'
        ? 3 + Math.floor(r() * 6)
        : 1 + Math.floor(r() * 4);

    const flags: IntegrityFlagKind[] = [];
    if (passed && rounds <= 1) flags.push('low_iteration');

    const comments: TutorComment[] = [];
    if (profile === 'rusher' && r() < 0.35) {
      comments.push({
        author_role: 'tutor',
        text: 'Solution style differs from earlier submissions; asked to explain in lab.',
        created_at: new Date(submittedMs + 3600 * 1000).toISOString(),
      });
      flags.push('tutor_concern');
    } else if (r() < 0.08) {
      comments.push({
        author_role: 'tutor',
        text: 'Good approach, minor edge case missed.',
        created_at: new Date(submittedMs + 3600 * 1000).toISOString(),
      });
    }

    examples.push({
      content_id: `c-${seed}-${i}`,
      path,
      title,
      category: 'standard',
      score,
      passed,
      test_rounds: rounds,
      submitted_at: new Date(submittedMs).toISOString(),
      official: true,
      late,
      flags,
      comments,
      href: `/courses/${DEMO_COURSE_ID}/contents/c-${seed}-${i}`,
    });
  }

  // Velocity flag: many official submissions inside one 24h window.
  tagVelocityBursts(examples);
  return examples;
}

/** Flag examples that fall in a >=5-per-day official-submission burst. */
function tagVelocityBursts(examples: StandardExampleResult[]): void {
  const official = examples
    .filter((e) => e.official && e.submitted_at)
    .sort((a, b) => Date.parse(a.submitted_at!) - Date.parse(b.submitted_at!));
  const dayMs = 24 * 3600 * 1000;
  for (let i = 0; i < official.length; i += 1) {
    const window = official.filter(
      (e) => Math.abs(Date.parse(e.submitted_at!) - Date.parse(official[i].submitted_at!)) <= dayMs,
    );
    if (window.length >= 5 && !official[i].flags.includes('velocity')) {
      official[i].flags.push('velocity');
    }
  }
}

function timelineFromExamples(
  courseMemberId: string,
  examples: StandardExampleResult[],
): AnalyticsStudentTimeline {
  const events: AnalyticsTimelineEvent[] = [];
  for (const ex of examples) {
    if (!ex.submitted_at) continue;
    events.push({
      occurred_at: ex.submitted_at,
      event_type: 'submission',
      course_content_id: ex.content_id,
      path: ex.path,
      title: ex.title,
      artifact_id: null,
      result_id: null,
      grade: ex.score === null ? null : Math.round(ex.score * 100),
      status: ex.passed ? 1 : 0,
      submit: true,
      version_identifier: null,
      relation_to_submission_cutoff: ex.late ? 'after' : 'before',
    });
  }
  return {
    course_id: DEMO_COURSE_ID,
    course_member_id: courseMemberId,
    submission_cutoff: DEMO_SUBMISSION_CUTOFF,
    grading_cutoff: null,
    events,
  };
}

interface DemoRecord {
  student: DemoStudent;
  detail: DemoStudentDetail;
}

let cache: DemoRecord[] | null = null;

function build(): DemoRecord[] {
  if (cache) return cache;
  const cutoffMs = Date.parse(DEMO_SUBMISSION_CUTOFF);
  const records: DemoRecord[] = [];

  for (let i = 0; i < STUDENT_COUNT; i += 1) {
    const seed = 1000 + i * 7;
    const r = rng(seed);
    const profile = profileFor(rng(seed * 3));
    const courseMemberId = `m-${String(i).padStart(2, '0')}`;
    const examples = makeExamples(seed, profile, cutoffMs);

    const attempted = examples.filter((e) => e.official);
    const passed = attempted.filter((e) => e.passed);
    const scored = attempted.map((e) => e.score ?? 0);
    const submittedTimes = attempted
      .map((e) => e.submitted_at)
      .filter((t): t is string => t !== null);
    const flags = countFlags(examples);

    const student: DemoStudent = {
      course_member_id: courseMemberId,
      course_id: DEMO_COURSE_ID,
      user_id: `u-${i}`,
      username: `${FIRST[i].toLowerCase()}.${LAST[i].toLowerCase().replace(/[^a-z]/g, '')}`,
      given_name: FIRST[i],
      family_name: LAST[i],
      student_id: String(1010100 + i),
      total_max_assignments: N_STANDARD,
      total_submitted_assignments: attempted.length,
      submitted_percentage: pct(attempted.length, N_STANDARD),
      total_graded_assignments: attempted.length,
      graded_percentage: pct(attempted.length, N_STANDARD),
      average_grading: scored.length ? avg(scored) * 100 : null,
      latest_submission_at: submittedTimes.sort().at(-1) ?? null,
      late_submission_count: attempted.filter((e) => e.late).length,
      // integrity rollup
      standard_passed: passed.length,
      standard_total: N_STANDARD,
      pass_rate: pct(passed.length, N_STANDARD),
      average_score: scored.length ? avg(scored) : null,
      flags,
      worst_band: false,
    };

    records.push({
      student,
      detail: { timeline: timelineFromExamples(courseMemberId, examples), examples },
    });
    void r;
  }

  const band = markWorstBand(records.map((rec) => rec.student));
  records.forEach((rec, i) => {
    rec.student.worst_band = band.has(i);
  });

  cache = records;
  return records;
}

export function demoStudents(): DemoStudent[] {
  return build().map((r) => r.student);
}

export function demoStudentDetail(courseMemberId: string): DemoStudentDetail | null {
  return build().find((r) => r.student.course_member_id === courseMemberId)?.detail ?? null;
}

/** Synthetic source for an example, so the click-through shows real code in the
 * demo. Looked up by content_id across the generated roster. */
export function demoExampleSource(contentId: string): ExampleSource | null {
  for (const rec of build()) {
    const ex = rec.detail.examples.find((e) => e.content_id === contentId);
    if (!ex) continue;
    const fn = ex.path.split('.').pop() ?? 'solution';
    return {
      content_id: contentId,
      title: ex.title,
      href: ex.href ?? null,
      files: [
        {
          name: `${fn}.py`,
          content:
            `"""${ex.title} - reference solution."""\n\n` +
            `def ${fn}(values):\n` +
            `    """Return the running total of values."""\n` +
            `    total = 0\n` +
            `    for v in values:\n` +
            `        total += v\n` +
            `    return total\n\n\n` +
            `if __name__ == "__main__":\n` +
            `    print(${fn}([1, 2, 3, 4]))\n`,
        },
        {
          name: `test_${fn}.py`,
          content:
            `import pytest\n\n` +
            `from ${fn} import ${fn}\n\n\n` +
            `@pytest.mark.parametrize("values,expected", [\n` +
            `    ([], 0),\n` +
            `    ([1, 2, 3], 6),\n` +
            `    ([-1, 1], 0),\n` +
            `])\n` +
            `def test_${fn}(values, expected):\n` +
            `    assert ${fn}(values) == expected\n`,
        },
        {
          name: 'README.md',
          content: `# ${ex.title}\n\nImplement \`${fn}\` so the tests pass. Path: \`${ex.path}\`.\n`,
        },
      ],
    };
  }
  return null;
}

export function demoSummary(): AnalyticsCourseSummary {
  const students = demoStudents();
  const totalMax = students.length * N_STANDARD;
  const submitted = students.reduce((a, s) => a + s.total_submitted_assignments, 0);
  const passed = students.reduce((a, s) => a + s.standard_passed, 0);
  const scores = students.map((s) => s.average_score).filter((v): v is number => v !== null);
  return {
    course_id: DEMO_COURSE_ID,
    total_students: students.length,
    total_max_assignments: totalMax,
    total_submitted_assignments: submitted,
    submitted_percentage: pct(submitted, totalMax),
    total_graded_assignments: passed,
    graded_percentage: pct(passed, totalMax),
    average_grading: scores.length ? avg(scores) * 100 : null,
    latest_submission_at: DEMO_SUBMISSION_CUTOFF,
    submission_cutoff: DEMO_SUBMISSION_CUTOFF,
    grading_cutoff: null,
    latest_job: null,
  };
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, v));
}
function pct(n: number, d: number): number {
  return d ? Math.round((n / d) * 1000) / 10 : 0;
}
function avg(xs: number[]): number {
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}
