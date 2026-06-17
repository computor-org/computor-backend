'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import type { CourseGet } from 'types/generated';
import {
  AnalyticsApiError,
  analyticsRoleAtLeast,
  getCourseSummary,
  listAnalyticsCourses,
  listStudents,
  type AnalyticsCourseAccess,
  type AnalyticsCourseSummary,
  type AnalyticsCutoffs,
  type AnalyticsStudentCheckpoint,
} from '@/src/api/analytics';
import SummaryCards from '@/src/components/analytics/SummaryCards';
import CutoffControls from '@/src/components/analytics/CutoffControls';
import RefreshControl from '@/src/components/analytics/RefreshControl';
import StudentCheckpointTable from '@/src/components/analytics/StudentCheckpointTable';
import StudentTimelinePanel from '@/src/components/analytics/StudentTimelinePanel';

export default function LecturerAnalyticsPage() {
  const courseId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { courseHasAtLeast } = usePermissions();

  const [course, setCourse] = useState<CourseGet | null>(null);
  const [analyticsCourse, setAnalyticsCourse] = useState<AnalyticsCourseAccess | null>(null);
  const [cutoffs, setCutoffs] = useState<AnalyticsCutoffs>({});
  const [summary, setSummary] = useState<AnalyticsCourseSummary | null>(null);
  const [students, setStudents] = useState<AnalyticsStudentCheckpoint[]>([]);
  const [selected, setSelected] = useState<AnalyticsStudentCheckpoint | null>(null);
  const [loading, setLoading] = useState(true);
  const [emptyReason, setEmptyReason] = useState<'none' | 'no-snapshot' | 'forbidden' | 'error'>(
    'none',
  );
  const [errorText, setErrorText] = useState<string | null>(null);
  const canRefresh =
    courseHasAtLeast(courseId, '_lecturer') ||
    analyticsRoleAtLeast(analyticsCourse?.role, '_lecturer');

  const load = useCallback(async () => {
    setLoading(true);
    setErrorText(null);
    try {
      const [s, list] = await Promise.all([
        getCourseSummary(courseId, cutoffs),
        listStudents(courseId, cutoffs),
      ]);
      setSummary(s);
      setStudents(list.students ?? []);
      setEmptyReason('none');
    } catch (e) {
      setSummary(null);
      setStudents([]);
      if (e instanceof AnalyticsApiError && e.status === 404) {
        setEmptyReason('no-snapshot');
      } else if (e instanceof AnalyticsApiError && e.status === 403) {
        setEmptyReason('forbidden');
      } else {
        setEmptyReason('error');
        setErrorText(e instanceof Error ? e.message : 'Failed to load analytics.');
      }
    } finally {
      setLoading(false);
    }
  }, [courseId, cutoffs]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const [localRes, analyticsRes] = await Promise.allSettled([
          apiFetch(`${API_BASE_URL}/courses/${courseId}`),
          listAnalyticsCourses(),
        ]);
        if (cancelled) return;
        if (localRes.status === 'fulfilled' && localRes.value.ok) {
          setCourse(await localRes.value.json());
        }
        if (analyticsRes.status === 'fulfilled') {
          setAnalyticsCourse(
            analyticsRes.value.find((entry) => entry.course_id === courseId) ?? null,
          );
        }
      } catch {
        /* header is best-effort */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [courseId, authLoading, isAuthenticated]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    load();
  }, [authLoading, isAuthenticated, load]);

  // Keep the selected student in sync with the latest roster (drop if gone).
  useEffect(() => {
    if (!selected) return;
    const match = students.find((s) => s.course_member_id === selected.course_member_id);
    if (!match) setSelected(null);
  }, [students, selected]);

  return (
    <AuthenticatedLayout>
      <div className="space-y-6 p-2 md:p-4">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link
              href={course ? `/courses/${courseId}/lecturer` : '/lecturer/analytics'}
              className="text-sm text-blue-600 hover:underline print:hidden"
            >
              Back to{' '}
              {course?.title ||
                analyticsCourse?.title ||
                course?.path ||
                analyticsCourse?.path ||
                'Analytics'}
            </Link>
            <h1 className="mt-2 text-3xl font-bold text-gray-900">Course Analytics</h1>
            <p className="mt-1 text-sm text-gray-500">
              Submission and grading checkpoint from the latest analytics snapshot.
            </p>
          </div>
          <div className="flex items-center gap-2 print:hidden">
            <button
              type="button"
              onClick={() => window.print()}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Print report
            </button>
            {canRefresh && (
              <RefreshControl
                courseId={courseId}
                cutoffs={cutoffs}
                initialJob={summary?.latest_job ?? null}
                onRefreshed={load}
              />
            )}
          </div>
        </header>

        <div className="print:hidden">
          <CutoffControls
            key={`${cutoffs.submissionCutoff ?? ''}|${cutoffs.gradingCutoff ?? ''}`}
            value={cutoffs}
            onApply={setCutoffs}
            disabled={loading}
          />
        </div>

        {loading && <p className="text-sm text-gray-500">Loading analytics…</p>}

        {!loading && emptyReason === 'forbidden' && (
          <EmptyState
            title="No analytics access"
            message="You need a tutor role or higher on this course to view analytics."
          />
        )}
        {!loading && emptyReason === 'no-snapshot' && (
          <EmptyState
            title="No snapshot yet"
            message={
              canRefresh
                ? 'Run “Update data” to import the latest course data from the source site.'
                : 'A lecturer needs to run the first analytics update for this course.'
            }
          />
        )}
        {!loading && emptyReason === 'error' && (
          <EmptyState title="Could not load analytics" message={errorText ?? 'Unknown error.'} />
        )}

        {!loading && summary && emptyReason === 'none' && (
          <>
            <SummaryCards summary={summary} />
            <StudentCheckpointTable
              students={students}
              selectedId={selected?.course_member_id ?? null}
              onSelect={setSelected}
            />
            {selected && (
              <StudentTimelinePanel courseId={courseId} student={selected} cutoffs={cutoffs} />
            )}
          </>
        )}
      </div>
    </AuthenticatedLayout>
  );
}

function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="rounded-lg border-2 border-dashed border-gray-300 bg-white p-10 text-center">
      <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      <p className="mx-auto mt-1 max-w-md text-sm text-gray-500">{message}</p>
    </div>
  );
}
