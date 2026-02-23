'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { useAuth } from '@/src/contexts/AuthContext';
import { CourseMemberGradingsClient } from '@/src/generated/clients/CourseMemberGradingsClient';
import ProgressBar from '@/src/components/progress/ProgressBar';
import SubmissionDonutChart from '@/src/components/progress/SubmissionDonutChart';
import ContentTree from '@/src/components/progress/ContentTree';
import type { CourseMemberGradingsGet } from 'types/generated';

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

export default function StudentProgressPage() {
  const params = useParams();
  const courseId = params.id as string;
  const memberId = params.memberId as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();

  const [data, setData] = useState<CourseMemberGradingsGet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const result = await gradingsClient.getCourseMemberGradingsEndpointCourseMemberGradingsCourseMemberIdGet({
        courseMemberId: memberId,
        courseId,
      });
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load student progress');
    } finally {
      setLoading(false);
    }
  }, [courseId, memberId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    fetchData();
  }, [authLoading, isAuthenticated, fetchData]);

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

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6 max-w-6xl">
        {/* Header */}
        <div>
          <Link
            href={`/courses/${courseId}/tutor`}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 mb-2"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Course Progress
          </Link>
          <div className="flex items-center justify-between">
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
            <button
              onClick={fetchData}
              disabled={loading}
              className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
            >
              Refresh
            </button>
          </div>
        </div>

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
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

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
      </div>
    </AuthenticatedLayout>
  );
}
