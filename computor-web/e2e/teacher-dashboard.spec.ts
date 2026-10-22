import { test, expect, type Page, type Route } from '@playwright/test';
import {
  assignmentsOf,
  formatDueRelation,
  formatMinutes,
  sortFlags,
  stripMarks,
} from '../src/utils/courseAnalytics';
import { toGradeBody } from '../src/components/tutor/TutorGradeForm';
import type { ActivityEvent, FlagReason, TypicalError } from '../src/generated/types/courses';

/**
 * Teacher dashboard: typical errors, per-student history/timeline/flags, the
 * flagged roster and the tutor pages. The backend is mocked at the network
 * layer with synthetic data; the backend's own pytest covers the endpoints.
 * Set SCREENSHOT_DIR to also save a full-page screenshot of each view.
 */

const API_ORIGIN = 'http://localhost:8000';
const COURSE_ID = '00000000-0000-0000-0000-0000000000c1';
const ADA = '00000000-0000-0000-0000-00000000a0a0';
const BOB = '00000000-0000-0000-0000-00000000b0b0';
const LOOPS = '00000000-0000-0000-0000-0000000001c1';
const GROUP = '00000000-0000-0000-0000-0000000005g1';
const ARTIFACT = '00000000-0000-0000-0000-0000000000a1';

const USER = {
  id: 'u-lect',
  username: 'lect',
  email: 'lect@example.org',
  given_name: 'Lea',
  family_name: 'Lecturer',
  user_roles: [],
};

const T = (h: number) => new Date(Date.UTC(2026, 2, 2, 9) + h * 3600_000).toISOString();

const gradingRow = (id: string, given: string, progress: number) => ({
  course_member_id: id,
  course_id: COURSE_ID,
  given_name: given,
  family_name: 'Synthetic',
  student_id: id === ADA ? '0100001' : '0100002',
  total_max_assignments: 4,
  total_submitted_assignments: Math.round((progress / 100) * 4),
  overall_progress_percentage: progress,
  latest_submission_at: T(1),
  overall_average_grading: 0.8,
  by_content_type: [],
});

const FLAG_ADA: FlagReason[] = [
  {
    code: 'sudden_jump',
    severity: 'info',
    title: 'Sudden jump to full score',
    reason: 'From 20% to 100% between two consecutive test runs 5 min apart.',
    course_content_id: LOOPS,
    course_content_title: 'Loops',
  },
];
const FLAG_BOB: FlagReason[] = [
  { code: 'inactive', severity: 'warning', title: 'Inactive', reason: 'Last test run or submission 30 days ago.' },
  { code: 'low_progress', severity: 'warning', title: 'Low progress', reason: 'Submitted 0 of 4 assignments (0%).' },
];
const RULES = [
  { code: 'inactive', title: 'Inactive', description: 'No test run and no submission in the last 14 days.' },
];

const TYPICAL = {
  course_id: COURSE_ID,
  results_scanned: 4,
  results_without_report: 0,
  truncated: false,
  errors: [
    {
      course_content_id: LOOPS,
      course_content_title: 'Loops',
      test_name: 'unit / sum',
      message: 'AssertionError: assert <n> == <n>',
      occurrences: 3,
      affected_students: 2,
      last_seen_at: T(1),
      examples: [
        { result_id: 'r2', course_member_id: BOB, student_name: 'Bob Synthetic', created_at: T(1), message: 'AssertionError: assert 7 == 2' },
        { result_id: 'r1', course_member_id: ADA, student_name: 'Ada Synthetic', created_at: T(0), message: 'AssertionError: assert 1 == 2' },
      ],
    },
  ],
};

const ACTIVITY = {
  course_member_id: ADA,
  course_id: COURSE_ID,
  session_gap_minutes: 30,
  events: [
    { kind: 'grading', at: T(3), course_content_id: LOOPS, course_content_title: 'Loops', grade: 0.8, status: 'corrected', is_submission: true, feedback: 'Good, but name your variables.', graded_by: 'Tim Tutor' },
    { kind: 'test_run', at: T(0.17), course_content_id: LOOPS, course_content_title: 'Loops', result_id: 'r3', grade: 1, status: 'finished', is_submission: true },
    { kind: 'submission', at: T(0.15), course_content_id: LOOPS, course_content_title: 'Loops', artifact_id: ARTIFACT, is_submission: true },
    { kind: 'test_run', at: T(0.08), course_content_id: LOOPS, course_content_title: 'Loops', result_id: 'r2', grade: 0.2, status: 'finished', is_submission: false },
  ],
  timelines: [
    {
      course_content_id: LOOPS,
      course_content_title: 'Loops',
      test_runs: 2,
      submissions: 1,
      first_activity_at: T(0.08),
      last_activity_at: T(0.17),
      first_submission_at: T(0.15),
      last_submission_at: T(0.15),
      first_full_score_at: T(0.17),
      best_grade: 1,
      latest_grade: 1,
      active_days: 1,
      median_gap_minutes: 5,
      estimated_active_minutes: 5,
    },
  ],
  flags: FLAG_ADA,
  rules: RULES,
};

const STUDENT_DETAIL = { ...gradingRow(ADA, 'Ada', 50), nodes: [] };

const TUTOR_MEMBERS = [
  { id: ADA, user_id: 'u-ada', course_id: COURSE_ID, course_role_id: '_student', ungraded_submissions_count: 1, unread_message_count: 0, user: { id: 'u-ada', given_name: 'Ada', family_name: 'Synthetic', email: 'ada@example.org', is_service: false, banned: false } },
  { id: BOB, user_id: 'u-bob', course_id: COURSE_ID, course_role_id: '_student', ungraded_submissions_count: 0, unread_message_count: 2, user: { id: 'u-bob', given_name: 'Bob', family_name: 'Synthetic', email: 'bob@example.org', is_service: false, banned: false } },
];

const CONTENT_TYPE = { id: 'ct', slug: 'assignment', course_id: COURSE_ID, course_content_kind_id: 'assignment', color: '#6366f1' };
const TUTOR_CONTENT = {
  id: LOOPS,
  title: 'Loops',
  path: 'w1.loops',
  course_id: COURSE_ID,
  course_content_type_id: 'ct',
  course_content_kind_id: 'assignment',
  position: 1,
  course_content_type: CONTENT_TYPE,
  result_count: 2,
  submission_count: 1,
  color: '#6366f1',
  submitted: true,
  status: 'not_reviewed',
  unreviewed_count: 1,
  result: { id: 'r3', result: 1, result_json: { summary: { passed: 1, failed: 0, skipped: 0, total: 1 }, tests: [{ name: 'unit', result: 'PASSED', summary: { passed: 1, failed: 0, skipped: 0, total: 1 }, tests: [{ name: 'sum', result: 'PASSED' }] }] } },
  submission_group: { id: GROUP, latest_submitted_artifact_id: ARTIFACT, gradings: [] },
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

async function setup(page: Page) {
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify({
      id: user.id, username: user.username, email: user.email,
      givenName: user.given_name, familyName: user.family_name,
      role: 'user', systemRoles: [],
    }));
    sessionStorage.setItem('auth_provider', 'sso');
  }, USER);

  const calls: { method: string; path: string; search: string; body: unknown }[] = [];
  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const path = url.pathname;
    calls.push({ method: req.method(), path, search: url.search, body: req.postDataJSON?.() ?? null });

    if (path.startsWith('/user/views')) return json(route, ['lecturer', 'tutor']);
    if (path.endsWith('/user/scopes')) return json(route, { is_admin: false, course: { [COURSE_ID]: ['_lecturer'] } });
    if (path.endsWith('/user')) return json(route, USER);
    if (path.startsWith('/messages')) return json(route, []);
    if (path === `/courses/${COURSE_ID}`) return json(route, { id: COURSE_ID, title: 'Programming 101', path: 'prog.2026' });

    if (path === '/course-member-gradings') return json(route, [gradingRow(ADA, 'Ada', 50), gradingRow(BOB, 'Bob', 0)]);
    if (path === `/course-member-gradings/${ADA}`) return json(route, STUDENT_DETAIL);
    if (path === `/course-analytics/courses/${COURSE_ID}/typical-errors`) return json(route, TYPICAL);
    if (path === `/course-analytics/courses/${COURSE_ID}/flags`) {
      return json(route, {
        course_id: COURSE_ID,
        rules: RULES,
        students: [
          { course_member_id: ADA, student_name: 'Ada Synthetic', flags: FLAG_ADA },
          { course_member_id: BOB, student_name: 'Bob Synthetic', flags: FLAG_BOB },
        ],
      });
    }
    if (path === `/course-analytics/course-members/${ADA}/activity`) return json(route, ACTIVITY);

    if (path === '/tutors/course-members') return json(route, TUTOR_MEMBERS);
    if (path === `/tutors/course-members/${ADA}`) return json(route, { ...TUTOR_MEMBERS[0], unreviewed_course_contents: [] });
    if (path === `/tutors/course-members/${ADA}/course-contents`) return json(route, [TUTOR_CONTENT]);
    if (path === `/tutors/course-members/${ADA}/course-contents/${LOOPS}`) {
      if (req.method() === 'PATCH') return json(route, TUTOR_CONTENT);
      return json(route, TUTOR_CONTENT);
    }
    if (path === '/tutors/submission-groups') {
      return json(route, [{
        id: GROUP, course_id: COURSE_ID, course_content_id: LOOPS, display_name: 'Ada Synthetic',
        max_group_size: 1, member_count: 1, submission_count: 1, latest_submission_at: T(0.15),
        has_ungraded_submissions: true, created_at: T(0), updated_at: T(0),
      }]);
    }
    if (path === `/tutors/submission-groups/${GROUP}`) {
      return json(route, {
        id: GROUP, course_id: COURSE_ID, course_content_id: LOOPS, display_name: 'Ada Synthetic', max_group_size: 1,
        members: [{ id: 'sgm', course_member_id: ADA, user_id: 'u-ada', given_name: 'Ada', family_name: 'Synthetic' }],
        created_at: T(0), updated_at: T(0),
      });
    }
    if (path === '/course-contents') return json(route, [{ id: LOOPS, title: 'Loops', path: 'w1.loops' }]);
    return json(route, {});
  });
  return calls;
}

async function shot(page: Page, name: string) {
  const dir = process.env.SCREENSHOT_DIR;
  if (!dir) return;
  // The page scrolls inside its own container, so grow the viewport instead of fullPage.
  await page.setViewportSize({ width: 1440, height: 1800 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${dir}/${name}.png` });
}

// --- pure helpers ------------------------------------------------------------

test('durations and due relations read as words', () => {
  expect(formatMinutes(null)).toBe('—');
  expect(formatMinutes(45)).toBe('45 min');
  expect(formatMinutes(125)).toBe('2 h 5 min');
  expect(formatMinutes(60 * 27)).toBe('1 d 3 h');
  expect(formatDueRelation(1.5)).toBe('1 h 30 min before due');
  expect(formatDueRelation(-0.25)).toBe('15 min after due');
});

test('warnings lead the flag list', () => {
  const sorted = sortFlags([...FLAG_ADA, ...FLAG_BOB]);
  expect(sorted.map((f) => f.code)).toEqual(['inactive', 'low_progress', 'sudden_jump']);
});

test('strip marks are placed on the shared axis and clamped', () => {
  const ev = (kind: string, h: number): ActivityEvent => ({ kind, at: T(h), course_content_id: LOOPS });
  const start = Date.parse(T(0));
  const end = Date.parse(T(10));
  const marks = stripMarks([ev('test_run', 5), ev('grading', 6), ev('submission', 20)], start, end);
  expect(marks.map((m) => [m.kind, m.x])).toEqual([['test_run', 0.5], ['submission', 1]]);
  expect(stripMarks([ev('test_run', 3)], start, start)[0].x).toBe(0.5);
});

test('assignment options come from the error groups, once each', () => {
  const e = (id: string, title: string) => ({ course_content_id: id, course_content_title: title }) as TypicalError;
  expect(assignmentsOf([e('b', 'Lists'), e('a', 'Loops'), e('b', 'Lists')])).toEqual([
    { id: 'b', title: 'Lists' },
    { id: 'a', title: 'Loops' },
  ]);
});

test('grade form converts percent to a fraction and validates', () => {
  expect(toGradeBody('85', 'corrected', ' well done ', 'a1')).toEqual({
    grade: 0.85, status: 1, feedback: 'well done', artifact_id: 'a1',
  });
  expect(toGradeBody('', 'correction_necessary', '')).toEqual({
    grade: null, status: 2, feedback: null, artifact_id: null,
  });
  expect(toGradeBody('72,5', 'improvement_possible', 'x')).toMatchObject({ grade: 0.725, status: 3 });
  expect(typeof toGradeBody('120', 'corrected', '')).toBe('string');
});

// --- pages -------------------------------------------------------------------

test('typical errors page groups failures and links examples to the student', async ({ page }) => {
  await setup(page);
  await page.goto(`/courses/${COURSE_ID}/lecturer/typical-errors`);
  await expect(page.getByRole('heading', { name: 'Typical errors' })).toBeVisible();
  const row = page.getByRole('row', { name: /unit \/ sum/ });
  await expect(row).toContainText('AssertionError: assert <n> == <n>');
  await row.click();
  const link = page.getByRole('link', { name: 'Bob Synthetic' });
  await expect(link).toHaveAttribute('href', `/courses/${COURSE_ID}/lecturer/grading/${BOB}`);
  await expect(page.getByText('AssertionError: assert 7 == 2')).toBeVisible();
  await shot(page, 'typical-errors');
});

test('grading roster shows flags with reasons and can filter to flagged', async ({ page }) => {
  await setup(page);
  await page.goto(`/courses/${COURSE_ID}/lecturer/grading`);
  await expect(page.getByText('2 of 2 students match at least one rule')).toBeVisible();
  const bob = page.getByRole('row', { name: /Bob Synthetic/ });
  await expect(bob.getByText('Low progress')).toBeVisible();
  await expect(bob.locator('[title*="Submitted 0 of 4"]')).toHaveCount(1);
  await shot(page, 'grading-roster-flags');
});

test('per-student page shows flags, attempt timeline and feedback history', async ({ page }) => {
  const calls = await setup(page);
  await page.goto(`/courses/${COURSE_ID}/lecturer/grading/${ADA}`);
  await expect(page.getByRole('heading', { name: 'Attempt timeline' })).toBeVisible();
  await expect(page.getByText('From 20% to 100% between two consecutive test runs 5 min apart.')).toBeVisible();
  await expect(page.getByText('Good, but name your variables.')).toBeVisible();
  await expect(page.getByText('by Tim Tutor')).toBeVisible();
  await expect(page.getByText('Submission run')).toBeVisible();
  await page.getByLabel('Filter by kind').selectOption('grading');
  await expect(page.getByText('Submission run')).toHaveCount(0);
  expect(calls.some((c) => c.path === `/course-analytics/course-members/${ADA}/activity`)).toBe(true);
  await shot(page, 'student-activity');
});

test('tutor queue opens the student grading page and saves a grade', async ({ page }) => {
  const calls = await setup(page);
  await page.goto(`/courses/${COURSE_ID}/tutor/submissions`);
  await expect(page.getByRole('row', { name: /Ada Synthetic/ })).toContainText('Loops');
  await shot(page, 'tutor-submissions');
  await page.getByRole('row', { name: /Ada Synthetic/ }).click();
  await expect(page).toHaveURL(new RegExp(`/tutor/grading/${ADA}\\?content=${LOOPS}`));
  await expect(page.getByRole('heading', { name: 'Grade the latest submission' })).toBeVisible();
  await page.getByLabel('Grade (%)').fill('85');
  await page.getByLabel('Feedback for the student').fill('Well structured.');
  await page.getByRole('button', { name: 'Save grade' }).click();
  await expect(page.getByText('Grade saved.')).toBeVisible();
  const patch = calls.find((c) => c.method === 'PATCH');
  expect(patch?.path).toBe(`/tutors/course-members/${ADA}/course-contents/${LOOPS}`);
  expect(patch?.body).toEqual({ grade: 0.85, status: 1, feedback: 'Well structured.', artifact_id: ARTIFACT });
  await shot(page, 'tutor-grading');
});

test('tutor overview counts waiting work', async ({ page }) => {
  await setup(page);
  await page.goto(`/courses/${COURSE_ID}/tutor`);
  await expect(page.getByText('Students with ungraded work')).toBeVisible();
  await expect(page.getByRole('link', { name: /Submissions to review/ })).toBeVisible();
  await shot(page, 'tutor-overview');
});
