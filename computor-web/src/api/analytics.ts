/**
 * Lecturer analytics API client.
 *
 * Response/request shapes are the generated types from the backend Pydantic
 * models (`computor_types/analytics.py` -> `generated/types/analytics`); this
 * module only adds the fetch wrappers and small status helpers. Regenerate the
 * types with `bash generate.sh types` (or `... --categories analytics`).
 *
 * Every endpoint is enforced server-side: read needs course role `_tutor`+,
 * refresh needs `_lecturer`+, admins bypass. The UI gates the same way for UX
 * but the backend is the authority.
 */

import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import type {
  AnalyticsCourseAccess,
  AnalyticsCourseSummary,
  AnalyticsJobStatus,
  AnalyticsRefreshRequest,
  AnalyticsStudentCheckpoint,
  AnalyticsStudentList,
  AnalyticsStudentReport,
  AnalyticsStudentTimeline,
} from '@/src/generated/types/analytics';
import type { CourseContentLecturerList } from '@/src/generated/types/courses';
import type {
  ExampleSource,
  StandardExampleResult,
  StudentIntegrity,
} from '@/src/components/analytics/integrity';
import {
  DEMO_COURSE_ID,
  demoExampleSource,
  demoStudentDetail,
  demoStudents,
  demoSummary,
} from '@/src/components/analytics/demoData';

/** Roster row: the checkpoint plus the integrity rollup once the backend
 * provides it (optional until those aggregations land). */
export type RosterStudent = AnalyticsStudentCheckpoint & Partial<StudentIntegrity>;

/** Local UI testing against synthetic data, no backend. Set
 * NEXT_PUBLIC_ANALYTICS_DEMO=1 (see computor-web/.env.local.example). */
export const IS_DEMO = process.env.NEXT_PUBLIC_ANALYTICS_DEMO === '1';

export type {
  AnalyticsCourseAccess,
  AnalyticsCourseSummary,
  AnalyticsJobStatus,
  AnalyticsRefreshRequest,
  AnalyticsStudentCheckpoint,
  AnalyticsStudentList,
  AnalyticsStudentReport,
  AnalyticsStudentTimeline,
  AnalyticsTimelineEvent,
} from '@/src/generated/types/analytics';

/** UI-side cutoff parameters (camelCase), mapped to the API's snake_case query. */
export interface AnalyticsCutoffs {
  submissionCutoff?: string | null;
  gradingCutoff?: string | null;
}

/** No cutoffs by default — a preset date would silently hide submissions
 * made after it. Cutoffs are course-specific and set in the UI. */
export const DEFAULT_ANALYTICS_CUTOFFS: AnalyticsCutoffs = {
  submissionCutoff: null,
  gradingCutoff: null,
};

/** Carries the HTTP status so callers can distinguish 403 (no access) from 404
 * (no snapshot yet) and render the right empty/error state. */
export class AnalyticsApiError extends Error {
  constructor(
    public status: number,
    public body: string,
  ) {
    super(body || `Request failed with status ${status}`);
    this.name = 'AnalyticsApiError';
  }
}

const base = (courseId: string) =>
  `${API_BASE_URL}/analytics/courses/${encodeURIComponent(courseId)}`;

const COURSE_ROLE_RANK: Record<string, number> = {
  _owner: 5,
  _maintainer: 4,
  _lecturer: 3,
  _tutor: 2,
  _student: 1,
};

const COURSE_ROLE_LABEL: Record<string, string> = {
  _owner: 'Owner',
  _maintainer: 'Maintainer',
  _lecturer: 'Lecturer',
  _tutor: 'Tutor',
  _student: 'Student',
};

function cutoffQuery(cutoffs?: AnalyticsCutoffs): string {
  const params = new URLSearchParams();
  if (cutoffs?.submissionCutoff) params.set('submission_cutoff', cutoffs.submissionCutoff);
  if (cutoffs?.gradingCutoff) params.set('grading_cutoff', cutoffs.gradingCutoff);
  const q = params.toString();
  return q ? `?${q}` : '';
}

async function safeText(res: Response): Promise<string> {
  try {
    return await res.text();
  } catch {
    return '';
  }
}

async function getJson<T>(url: string): Promise<T> {
  const res = await apiFetch(url);
  if (!res.ok) {
    throw new AnalyticsApiError(res.status, await safeText(res));
  }
  return (await res.json()) as T;
}

export function getCourseSummary(
  courseId: string,
  cutoffs?: AnalyticsCutoffs,
): Promise<AnalyticsCourseSummary> {
  if (IS_DEMO) return Promise.resolve(demoSummary());
  return getJson(`${base(courseId)}/summary${cutoffQuery(cutoffs)}`);
}

export function listAnalyticsCourses(): Promise<AnalyticsCourseAccess[]> {
  if (IS_DEMO) {
    return Promise.resolve([
      { course_id: DEMO_COURSE_ID, title: 'Demo: Programming in the AI Era', path: 'demo',
        source_name: 'demo', role: '_lecturer', total_students: demoStudents().length,
        latest_job: null },
    ]);
  }
  return getJson(`${API_BASE_URL}/analytics/courses`);
}

export function listStudents(
  courseId: string,
  cutoffs?: AnalyticsCutoffs,
): Promise<AnalyticsStudentList> {
  if (IS_DEMO) return Promise.resolve({ students: demoStudents(), gradings: [] });
  return getJson(`${base(courseId)}/students${cutoffQuery(cutoffs)}`);
}

export function listCourseContentsForFind(courseId: string): Promise<CourseContentLecturerList[]> {
  if (IS_DEMO) return Promise.resolve([]);
  return getJson<CourseContentLecturerList[]>(
    `${API_BASE_URL}/lecturers/course-contents?course_id=${encodeURIComponent(courseId)}&limit=2000`,
  ).catch((e) => {
    if (e instanceof AnalyticsApiError) return [];
    throw e;
  });
}

/** Source files of one example, shown in a modal so the lecturer reads the code
 * without leaving the student detail. Demo returns synthetic source; the real
 * endpoint lands with the backend aggregations. */
export function getExampleSource(
  courseId: string,
  contentId: string,
): Promise<ExampleSource | null> {
  if (IS_DEMO) return Promise.resolve(demoExampleSource(contentId));
  return getJson<ExampleSource>(
    `${base(courseId)}/examples/${encodeURIComponent(contentId)}/source`,
  ).catch((e) => {
    if (e instanceof AnalyticsApiError && e.status === 404) return null;
    throw e;
  });
}

/** Per-student standard-example evidence (score-pass, test rounds, flags,
 * comments) for the detail view. Empty until the backend endpoint lands; the
 * demo generator fills it for local testing. */
export function getStudentExamples(
  courseId: string,
  courseMemberId: string,
  cutoffs?: AnalyticsCutoffs,
): Promise<StandardExampleResult[]> {
  if (IS_DEMO) return Promise.resolve(demoStudentDetail(courseMemberId)?.examples ?? []);
  return getJson<StandardExampleResult[]>(
    `${base(courseId)}/students/${encodeURIComponent(courseMemberId)}/examples${cutoffQuery(cutoffs)}`,
  ).catch((e) => {
    if (e instanceof AnalyticsApiError && e.status === 404) return [];
    throw e;
  });
}

export function getStudentReport(
  courseId: string,
  courseMemberId: string,
  cutoffs?: AnalyticsCutoffs,
): Promise<AnalyticsStudentReport> {
  return getJson(
    `${base(courseId)}/students/${encodeURIComponent(courseMemberId)}${cutoffQuery(cutoffs)}`,
  );
}

export function getStudentTimeline(
  courseId: string,
  courseMemberId: string,
  cutoffs?: AnalyticsCutoffs,
): Promise<AnalyticsStudentTimeline> {
  if (IS_DEMO) {
    const detail = demoStudentDetail(courseMemberId);
    if (!detail) return Promise.reject(new AnalyticsApiError(404, 'no demo student'));
    return Promise.resolve(detail.timeline);
  }
  return getJson(
    `${base(courseId)}/students/${encodeURIComponent(courseMemberId)}/timeline${cutoffQuery(cutoffs)}`,
  );
}

export function listJobs(courseId: string, limit = 20): Promise<AnalyticsJobStatus[]> {
  return getJson(`${base(courseId)}/jobs?limit=${limit}`);
}

export function getJob(jobId: string): Promise<AnalyticsJobStatus> {
  return getJson(`${API_BASE_URL}/analytics/jobs/${encodeURIComponent(jobId)}`);
}

export async function triggerRefresh(
  courseId: string,
  request: AnalyticsRefreshRequest,
): Promise<AnalyticsJobStatus> {
  const res = await apiFetch(`${base(courseId)}/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    throw new AnalyticsApiError(res.status, await safeText(res));
  }
  return (await res.json()) as AnalyticsJobStatus;
}

/** A job that has reached a terminal state no longer needs polling. */
export function isTerminalJob(status: string): boolean {
  return ['completed', 'succeeded', 'success', 'failed', 'error', 'cancelled'].includes(
    status.toLowerCase(),
  );
}

export function isFailedJob(status: string): boolean {
  return ['failed', 'error', 'cancelled'].includes(status.toLowerCase());
}

export function analyticsRoleAtLeast(
  role: string | null | undefined,
  minRole: string,
): boolean {
  if (!role) return false;
  return (COURSE_ROLE_RANK[role] ?? 0) >= (COURSE_ROLE_RANK[minRole] ?? Number.MAX_SAFE_INTEGER);
}

export function analyticsRoleLabel(role: string | null | undefined): string | null {
  if (!role) return null;
  return COURSE_ROLE_LABEL[role] ?? role.replace(/^_/, '');
}
