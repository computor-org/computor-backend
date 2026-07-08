'use client';

import { useMemo } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea } from '@/src/components/ListPageLayout';
import ErrorBanner from '@/src/components/ErrorBanner';
import { useResource } from '@/src/hooks/useResource';
import { CourseMemberGradingsClient } from '@/src/generated/clients/CourseMemberGradingsClient';
import ProgressBar from '@/src/components/progress/ProgressBar';
import ContentTree from '@/src/components/progress/ContentTree';
import SubmissionCurve from '@/src/components/progress/SubmissionCurve';
import { usePersistedCourseDate } from '@/src/hooks/usePersistedCourseDate';

// Pulls in recharts — load only when this page renders (keeps the shared
// bundle free of the charting library).
const SubmissionDonutChart = dynamic(
  () => import('@/src/components/progress/SubmissionDonutChart'),
  { ssr: false, loading: () => <div className="h-48 bg-gray-100 rounded animate-pulse" /> },
);

const gradingsClient = new CourseMemberGradingsClient();

function relativeDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Never';
  const days = Math.floor((Date.now() - new Date(dateStr).getTime()) / (1000 * 60 * 60 * 24));
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  return `${Math.floor(days / 30)} months ago`;
}

// `<input type="datetime-local">` works in the browser's local time and has no
// timezone; convert an ISO instant to the matching input value and back.
function isoToLocalInput(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function StudentProgressPage() {
  const params = useParams();
  const courseId = params.id as string;
  const memberId = params.memberId as string;

  const { data, loading, error, reload } = useResource(
    () =>
      gradingsClient.getCourseMemberGradingsEndpointCourseMemberGradingsCourseMemberIdGet({
        courseMemberId: memberId,
        courseId,
      }),
    [courseId, memberId],
  );

  // Start/due dates persist in localStorage — scoped per course, with a global
  // "last-used" fallback so a not-yet-configured course pre-fills with the last
  // dates set anywhere. The start date windows the curve; the due date is drawn
  // as a guide and flags late work.
  const [startDate, onStartDateChange] = usePersistedCourseDate(courseId, 'start-date');
  const [dueDate, onDueDateChange] = usePersistedCourseDate(courseId, 'due-date');

  const studentName = data
    ? `${data.given_name || ''} ${data.family_name || ''}`.trim() || data.username || 'Unknown'
    : '';

  const gradePercent = data?.overall_average_grading != null
    ? Math.round(data.overall_average_grading * 100)
    : null;

  const progressPercent = data
    ? Math.round(data.overall_progress_percentage)
    : 0;

  const remaining = data
    ? Math.max(0, data.total_max_assignments - data.total_submitted_assignments)
    : 0;

  // One point per submittable assignment that has an official submission,
  // using its latest official submission time — the curve's raw material.
  const submissionPoints = useMemo(
    () =>
      (data?.nodes ?? [])
        .filter((n) => n.submittable && n.latest_submission_at)
        .map((n) => ({ at: n.latest_submission_at as string, label: n.title })),
    [data],
  );

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <div id="printable-report" className="contents">
          {/* Header */}
          <div>
            <Link
              href={`/courses/${courseId}/lecturer/students`}
              className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 mb-2 print:hidden"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Students
            </Link>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {loading ? 'Student Progress' : studentName}
                </h1>
                {data?.student_id && (
                  <p className="text-sm text-gray-500 font-mono mt-0.5">Matr. {data.student_id}</p>
                )}
                {data && (
                  <p className="text-xs text-gray-400 mt-1">
                    Last active: {relativeDate(data.latest_submission_at)}
                  </p>
                )}
              </div>
              <div className="flex items-end gap-2 print:hidden">
                <div className="flex flex-col gap-1">
                  <label htmlFor="start-date" className="text-xs font-medium text-gray-600">
                    Start date
                  </label>
                  <input
                    id="start-date"
                    type="datetime-local"
                    value={isoToLocalInput(startDate)}
                    onChange={(e) => onStartDateChange(e.target.value)}
                    className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label htmlFor="due-date" className="text-xs font-medium text-gray-600">
                    Due date
                  </label>
                  <input
                    id="due-date"
                    type="datetime-local"
                    value={isoToLocalInput(dueDate)}
                    onChange={(e) => onDueDateChange(e.target.value)}
                    className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <button
                  onClick={() => window.print()}
                  className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                >
                  Print
                </button>
                <button
                  onClick={() => reload()}
                  disabled={loading}
                  className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                >
                  Refresh
                </button>
              </div>
            </div>
          </div>

          <ScrollArea className="space-y-6 print:overflow-visible">
          {/* Loading */}
          {loading && (
            <div className="space-y-4">
              <div className="h-32 bg-gray-100 rounded-lg animate-pulse" />
              <div className="grid grid-cols-2 gap-4">
                <div className="h-72 bg-gray-100 rounded-lg animate-pulse" />
                <div className="h-72 bg-gray-100 rounded-lg animate-pulse" />
              </div>
            </div>
          )}

          {/* Error */}
          <ErrorBanner>{error}</ErrorBanner>

          {/* Content */}
          {!loading && !error && data && (
            <>
              {/* Overall Progress Card */}
              <div className="bg-white rounded-lg border border-gray-200 p-5">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Grade */}
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Average Grade</p>
                    <p className="text-3xl font-bold text-gray-900">
                      {gradePercent != null ? `${gradePercent}%` : '-'}
                    </p>
                    {gradePercent != null && (
                      <div className="mt-2">
                        <ProgressBar value={gradePercent} color={gradePercent >= 50 ? '#22c55e' : '#ef4444'} />
                      </div>
                    )}
                  </div>

                  {/* Overall Progress */}
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Overall Progress</p>
                    <p className="text-3xl font-bold text-gray-900">{progressPercent}%</p>
                    <div className="mt-2">
                      <ProgressBar value={progressPercent} color="#6366f1" />
                    </div>
                  </div>

                  {/* Stats */}
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Submissions</p>
                    <div className="space-y-1.5 mt-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Submitted</span>
                        <span className="font-medium text-gray-900">
                          {data.total_submitted_assignments} / {data.total_max_assignments}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Remaining</span>
                        <span className="font-medium text-gray-900">{remaining}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Submission timeline (cumulative curve vs. due date) */}
              <SubmissionCurve
                points={submissionPoints}
                total={data.total_max_assignments}
                startDate={startDate}
                dueDate={dueDate}
              />

              {/* Charts Row */}
              <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
                {/* Donut Chart */}
                <SubmissionDonutChart
                  byContentType={data.by_content_type || []}
                  totalMax={data.total_max_assignments}
                  totalSubmitted={data.total_submitted_assignments}
                />

                {/* Content Type Breakdown */}
                <div className="bg-white rounded-lg border border-gray-200 p-5">
                  <h3 className="text-sm font-semibold text-gray-900 mb-4">Content Type Breakdown</h3>
                  <div className="space-y-4">
                    {(data.by_content_type || []).map(ct => {
                      const pct = Math.round(ct.progress_percentage);
                      const gradeStr = ct.average_grading != null
                        ? `${Math.round(ct.average_grading * 100)}%`
                        : '-';
                      return (
                        <div key={ct.course_content_type_id}>
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span
                                className="inline-block w-2.5 h-2.5 rounded-full"
                                style={{ backgroundColor: ct.course_content_type_color || '#6366f1' }}
                              />
                              <span className="text-sm font-medium text-gray-700">
                                {ct.course_content_type_title || ct.course_content_type_slug}
                              </span>
                            </div>
                            <span className="text-xs text-gray-500">
                              {ct.submitted_assignments}/{ct.max_assignments} ({pct}%) | Grade: {gradeStr}
                            </span>
                          </div>
                          <ProgressBar
                            value={ct.progress_percentage}
                            color={ct.course_content_type_color || '#6366f1'}
                            size="sm"
                          />
                        </div>
                      );
                    })}
                    {(!data.by_content_type || data.by_content_type.length === 0) && (
                      <p className="text-sm text-gray-500">No content type data available.</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Content Tree */}
              <ContentTree nodes={data.nodes || []} />
            </>
          )}
          </ScrollArea>
        </div>
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
