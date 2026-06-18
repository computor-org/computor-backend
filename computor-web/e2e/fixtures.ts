import type { Page, Route } from '@playwright/test';

/**
 * E2E test scaffolding: seed the client auth session and mock the backend at the
 * network layer so the lecturer analytics page can be driven without a real API.
 */

export const COURSE_ID = '11111111-1111-1111-1111-111111111111';
export const LOCAL_COURSE_ID = '44444444-4444-4444-4444-444444444444';
export const MEMBER_ID = '22222222-2222-2222-2222-222222222222';
const API_ORIGIN = 'http://localhost:8000';

const SUBMISSION_CUTOFF = '2026-06-18T22:01:00.000Z';

const SUMMARY = {
  course_id: COURSE_ID,
  total_students: 2,
  total_max_assignments: 10,
  total_submitted_assignments: 7,
  submitted_percentage: 70,
  total_graded_assignments: 5,
  graded_percentage: 50,
  average_grading: 82.5,
  latest_submission_at: '2026-06-18T20:30:00.000Z',
  submission_cutoff: SUBMISSION_CUTOFF,
  grading_cutoff: null,
  latest_job: null,
};

const STUDENTS = {
  students: [
    {
      course_member_id: MEMBER_ID,
      course_id: COURSE_ID,
      user_id: 'u1',
      username: 'astudent',
      given_name: 'Ada',
      family_name: 'Lovelace',
      student_id: '01234567',
      total_max_assignments: 10,
      total_submitted_assignments: 9,
      submitted_percentage: 90,
      total_graded_assignments: 8,
      graded_percentage: 80,
      average_grading: 91,
      latest_submission_at: '2026-06-18T20:30:00.000Z',
      late_submission_count: 1,
      standard_passed: 8,
      standard_total: 10,
      pass_rate: 80,
      average_score: 0.84,
      flags: { velocity: 2, low_iteration: 1, tutor_concern: 1, total: 4 },
      worst_band: true,
    },
    {
      course_member_id: '33333333-3333-3333-3333-333333333333',
      course_id: COURSE_ID,
      user_id: 'u2',
      username: 'bstudent',
      given_name: 'Grace',
      family_name: 'Hopper',
      student_id: '07654321',
      total_max_assignments: 10,
      total_submitted_assignments: 5,
      submitted_percentage: 50,
      total_graded_assignments: 2,
      graded_percentage: 20,
      average_grading: 64,
      latest_submission_at: '2026-06-17T10:00:00.000Z',
      late_submission_count: 0,
      standard_passed: 4,
      standard_total: 10,
      pass_rate: 40,
      average_score: 0.55,
      flags: { velocity: 0, low_iteration: 0, tutor_concern: 0, total: 0 },
      worst_band: false,
    },
  ],
  gradings: [],
};

const EXAMPLES = [
  {
    content_id: 'cc-1',
    path: 'week_1.intro',
    title: 'Week 1 · Intro',
    category: 'standard',
    score: 0.92,
    passed: true,
    test_rounds: 4,
    submitted_at: '2026-06-15T09:00:00.000Z',
    official: true,
    late: false,
    flags: [],
    comments: [],
    href: `/courses/${COURSE_ID}/contents/cc-1`,
  },
  {
    content_id: 'cc-2',
    path: 'week_2.loops',
    title: 'Week 2 · Loops',
    category: 'standard',
    score: 0.7,
    passed: true,
    test_rounds: 0,
    submitted_at: '2026-06-18T21:30:00.000Z',
    official: true,
    late: false,
    flags: ['low_iteration', 'velocity'],
    comments: [
      {
        author_role: 'tutor',
        text: 'Solution style differs from earlier submissions; asked to explain in lab.',
        created_at: '2026-06-18T22:30:00.000Z',
      },
    ],
    href: `/courses/${COURSE_ID}/contents/cc-2`,
  },
];

const TIMELINE = {
  course_id: COURSE_ID,
  course_member_id: MEMBER_ID,
  submission_cutoff: SUBMISSION_CUTOFF,
  grading_cutoff: null,
  events: [
    {
      occurred_at: '2026-06-15T09:00:00.000Z',
      event_type: 'submission',
      title: 'Assignment 1',
      submit: true,
      relation_to_submission_cutoff: 'before',
    },
    {
      occurred_at: '2026-06-17T18:00:00.000Z',
      event_type: 'submission',
      title: 'Assignment 2',
      submit: true,
      relation_to_submission_cutoff: 'before',
    },
    {
      occurred_at: '2026-06-19T08:00:00.000Z',
      event_type: 'submission',
      title: 'Assignment 3 (resubmit)',
      submit: true,
      relation_to_submission_cutoff: 'after',
    },
  ],
};

const EXAMPLE_SOURCE = {
  content_id: 'cc-2',
  title: 'Week 2 · Loops',
  href: `/courses/${COURSE_ID}/contents/cc-2`,
  files: [
    { name: 'loops.py', content: 'def loops(values):\n    return sum(values)\n' },
    { name: 'test_loops.py', content: 'def test_loops():\n    assert loops([1, 2]) == 3\n' },
  ],
};

const RUNNING_JOB = {
  job_id: 'job-1',
  course_id: COURSE_ID,
  source_name: 'green',
  status: 'running',
  progress: {},
  created_at: '2026-06-18T12:00:00.000Z',
  started_at: '2026-06-18T12:00:01.000Z',
  finished_at: null,
  row_counts: {},
  high_water_marks: {},
  error: null,
};

const COMPLETED_JOB = {
  ...RUNNING_JOB,
  status: 'completed',
  finished_at: '2026-06-18T12:00:05.000Z',
  row_counts: { course_member: 2, submission_artifact: 12 },
};

const USER = {
  id: 'u-self',
  username: 'lecturer1',
  email: 'lecturer1@example.org',
  given_name: 'Lee',
  family_name: 'Turing',
  user_roles: [],
};

const COURSE = { id: COURSE_ID, title: 'Test Course', path: 'test.course' };
const LOCAL_COURSE = {
  id: LOCAL_COURSE_ID,
  title: 'Local Blue Course',
  path: 'local.blue',
};
const ANALYTICS_COURSE = {
  course_id: COURSE_ID,
  title: COURSE.title,
  path: COURSE.path,
  source_name: 'green',
  role: '_lecturer',
  total_students: 2,
  latest_job: null,
};

type Role = '_lecturer' | '_tutor';
type Scenario = 'data' | 'empty';

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}

export async function setupAnalytics(
  page: Page,
  { role = '_lecturer', scenario = 'data' }: { role?: Role; scenario?: Scenario } = {},
): Promise<void> {
  // Seed the cached SSO user so AuthContext treats the session as logged in.
  await page.addInitScript((user) => {
    sessionStorage.setItem('auth_user', JSON.stringify(user));
  }, {
    id: USER.id,
    username: USER.username,
    email: USER.email,
    givenName: USER.given_name,
    familyName: USER.family_name,
    role: 'lecturer',
    systemRoles: [],
    permissions: [],
    courses: [COURSE_ID],
  });

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    const studentsBase = `/analytics/courses/${COURSE_ID}/students`;

    if (path.endsWith('/user/views')) return json(route, ['lecturer']);
    if (path.endsWith('/user/scopes'))
      return json(route, {
        is_admin: false,
        course: { [LOCAL_COURSE_ID]: ['_student'] },
      });
    if (path.endsWith('/user')) return json(route, USER);
    if (path === '/courses') return json(route, [LOCAL_COURSE]);
    if (path === `/courses/${COURSE_ID}`) return json(route, { detail: 'not found' }, 404);
    if (path === '/analytics/courses') {
      return json(route, [{ ...ANALYTICS_COURSE, role }]);
    }

    if (path.endsWith('/refresh') && method === 'POST') return json(route, RUNNING_JOB);
    if (path.includes('/analytics/jobs/')) return json(route, COMPLETED_JOB);

    if (path.endsWith('/summary')) {
      return scenario === 'empty' ? json(route, { detail: 'no snapshot' }, 404) : json(route, SUMMARY);
    }
    if (path.endsWith('/timeline')) return json(route, TIMELINE);
    if (path.endsWith('/source')) return json(route, EXAMPLE_SOURCE);
    if (path.endsWith('/examples')) return json(route, scenario === 'empty' ? [] : EXAMPLES);
    if (path === studentsBase) {
      return scenario === 'empty' ? json(route, { detail: 'no snapshot' }, 404) : json(route, STUDENTS);
    }

    return json(route, { detail: 'not found' }, 404);
  });
}

export function analyticsUrl(): string {
  return `/courses/${COURSE_ID}/lecturer/analytics`;
}
