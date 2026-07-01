'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import EmptyState from '@/src/components/EmptyState';
import { useAuth } from '@/src/contexts/AuthContext';
import {
  analyticsRoleLabel,
  listAnalyticsCourses,
  type AnalyticsCourseAccess,
} from '@/src/api/analytics';

export default function LecturerAnalyticsIndexPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [courses, setCourses] = useState<AnalyticsCourseAccess[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const result = await listAnalyticsCourses();
        if (!cancelled) setCourses(result);
      } catch (e) {
        if (!cancelled) {
          setCourses([]);
          setError(e instanceof Error ? e.message : 'Failed to load analytics courses.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, isAuthenticated]);

  return (
    <AuthenticatedLayout>
      <div className="space-y-6 p-6">
        <PageHeader
          breadcrumbs={[{ label: 'Analytics Snapshots' }]}
          title="Analytics Snapshots"
          subtitle={<span className="text-sm">Courses imported from authenticated analytics sources.</span>}
          actions={
            <Link href="/dashboard" className="text-sm font-medium text-blue-600 hover:underline">
              Dashboard
            </Link>
          }
        />

        {loading && <p className="text-sm text-gray-500">Loading analytics courses...</p>}
        {!loading && <ErrorBanner>{error}</ErrorBanner>}
        {!loading && !error && courses.length === 0 && (
          <EmptyState
            title="No analytics snapshots"
            description="No imported courses are available for your account."
          />
        )}
        {!loading && !error && courses.length > 0 && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {courses.map((course) => (
              <AnalyticsCourseCard key={course.course_id} course={course} />
            ))}
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}

function AnalyticsCourseCard({ course }: { course: AnalyticsCourseAccess }) {
  const role = analyticsRoleLabel(course.role);
  return (
    <Link href={`/courses/${course.course_id}/lecturer/analytics`}>
      <div className="flex h-full flex-col rounded-lg border border-gray-200 bg-white p-5 transition-all hover:border-blue-400 hover:shadow">
        <div className="flex items-start justify-between gap-3">
          <h2 className="text-lg font-semibold text-gray-900">
            {course.title || course.path || 'Untitled course'}
          </h2>
          {role && (
            <span className="shrink-0 rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
              {role}
            </span>
          )}
        </div>
        {course.path && <p className="mt-1 text-xs text-gray-500">{course.path}</p>}
        <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded bg-green-100 px-2 py-0.5 font-medium text-green-700">
            Analytics snapshot
          </span>
          <span className="rounded bg-gray-100 px-2 py-0.5 font-medium text-gray-700">
            Source {course.source_name}
          </span>
          <span className="text-gray-500">{course.total_students ?? 0} students</span>
        </div>
      </div>
    </Link>
  );
}
