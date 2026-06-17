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
  AnalyticsCourseSummary,
  AnalyticsJobStatus,
  AnalyticsRefreshRequest,
  AnalyticsStudentList,
  AnalyticsStudentReport,
  AnalyticsStudentTimeline,
} from '@/src/generated/types/analytics';

export type {
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
  return getJson(`${base(courseId)}/summary${cutoffQuery(cutoffs)}`);
}

export function listStudents(
  courseId: string,
  cutoffs?: AnalyticsCutoffs,
): Promise<AnalyticsStudentList> {
  return getJson(`${base(courseId)}/students${cutoffQuery(cutoffs)}`);
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
