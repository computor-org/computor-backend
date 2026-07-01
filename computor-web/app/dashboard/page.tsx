'use client';

import { type ReactNode, useEffect, useState } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import type { CourseList } from '@/src/generated/types/courses';
import {
  analyticsRoleLabel,
  listAnalyticsCourses,
  type AnalyticsCourseAccess,
} from '@/src/api/analytics';

type DashboardCourse = {
  id: string;
  title: string | null;
  path: string | null;
  local?: CourseList;
  analytics?: AnalyticsCourseAccess;
};

export default function DashboardPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { showManagement, isWorkspaceUser, isUserManager, isAdmin, courseRole } = usePermissions();
  const [courses, setCourses] = useState<CourseList[]>([]);
  const [analyticsCourses, setAnalyticsCourses] = useState<AnalyticsCourseAccess[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      const [localResult, analyticsResult] = await Promise.allSettled([
        fetchLocalCourses(),
        listAnalyticsCourses(),
      ]);
      if (cancelled) return;
      setCourses(localResult.status === 'fulfilled' ? localResult.value : []);
      setAnalyticsCourses(
        analyticsResult.status === 'fulfilled' ? analyticsResult.value : [],
      );
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, isAuthenticated]);

  const dashboardCourses = mergeDashboardCourses(courses, analyticsCourses);
  const actions = [
    { label: 'Browse Courses', href: '/courses', show: true },
    { label: 'Browse Examples', href: '/examples', show: true },
    { label: 'Analytics', href: '/lecturer/analytics', show: analyticsCourses.length > 0 || isAdmin },
    { label: 'Organizations', href: '/organizations', show: showManagement },
    { label: 'Course Families', href: '/course-families', show: showManagement },
    { label: 'Workspaces', href: '/workspaces', show: isWorkspaceUser },
    { label: 'User Management', href: '/admin/users', show: isUserManager },
    { label: 'System', href: '/admin/maintenance', show: isAdmin },
    { label: 'Settings', href: '/settings', show: true },
  ].filter((a) => a.show);

  return (
    <AuthenticatedLayout>
      <div className="space-y-6">
        {/* Welcome */}
        <div className="bg-white rounded-lg shadow p-6 border border-gray-200">
          <h1 className="text-3xl font-bold text-gray-900">
            Welcome back, {user?.givenName || user?.username}!
          </h1>
          <p className="mt-2 text-gray-600">
            {loading
              ? 'Loading your courses…'
              : dashboardCourses.length === 0
              ? "You're not enrolled in any courses yet."
              : `You have ${dashboardCourses.length} ${dashboardCourses.length === 1 ? 'course' : 'courses'}.`}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Your Courses */}
          <div className="bg-white rounded-lg shadow border border-gray-200">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold text-gray-900">Your Courses</h2>
              <Link href="/courses" className="text-sm text-blue-600 hover:underline">
                View all →
              </Link>
            </div>
            <div className="p-6">
              {loading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
                  ))}
                </div>
              ) : dashboardCourses.length === 0 ? (
                <p className="text-sm text-gray-500">No courses yet.</p>
              ) : (
                <div className="space-y-2">
                  {dashboardCourses.slice(0, 6).map((c) => {
                    const role = courseRole(c.id) ?? analyticsRoleLabel(c.analytics?.role);
                    const primaryHref = c.local
                      ? `/courses/${c.id}`
                      : `/courses/${c.id}/lecturer/analytics`;
                    return (
                      <div
                        key={c.id}
                        className="rounded-lg border border-gray-200 p-3 transition-colors hover:border-blue-400 hover:bg-blue-50"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <Link
                            href={primaryHref}
                            className="min-w-0 text-sm font-medium text-gray-900 hover:underline"
                          >
                            <span className="block truncate">{c.title || c.path}</span>
                          </Link>
                          {role && (
                            <span className="shrink-0 px-2 py-0.5 text-xs font-medium rounded bg-blue-100 text-blue-700">
                              {role}
                            </span>
                          )}
                        </div>
                        {c.title && c.path && <p className="text-xs text-gray-500">{c.path}</p>}
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          {c.local && <CourseBadge>Local</CourseBadge>}
                          {c.analytics && <CourseBadge tone="green">Analytics snapshot</CourseBadge>}
                          {c.analytics?.source_name && (
                            <CourseBadge tone="gray">Source {c.analytics.source_name}</CourseBadge>
                          )}
                          {c.analytics && (
                            <span className="text-xs text-gray-500">
                              {c.analytics.total_students ?? 0} students
                            </span>
                          )}
                          {c.analytics && c.local && (
                            <Link
                              href={`/courses/${c.id}/lecturer/analytics`}
                              className="ml-auto text-xs font-medium text-blue-600 hover:underline"
                            >
                              Analytics
                            </Link>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions — role-aware, real links */}
          <div className="bg-white rounded-lg shadow border border-gray-200">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">Quick Actions</h2>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-2 gap-3">
                {actions.map((a) => (
                  <Link
                    key={a.href}
                    href={a.href}
                    className="p-4 border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-center"
                  >
                    <p className="text-sm font-medium text-gray-700">{a.label}</p>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </AuthenticatedLayout>
  );
}

async function fetchLocalCourses(): Promise<CourseList[]> {
  const res = await apiFetch(`${API_BASE_URL}/courses`);
  if (!res.ok) return [];
  return (await res.json()) as CourseList[];
}

function mergeDashboardCourses(
  localCourses: CourseList[],
  analyticsCourses: AnalyticsCourseAccess[],
): DashboardCourse[] {
  const byId = new Map<string, DashboardCourse>();
  for (const course of localCourses) {
    byId.set(course.id, {
      id: course.id,
      title: course.title ?? null,
      path: course.path ?? null,
      local: course,
    });
  }
  for (const course of analyticsCourses) {
    const current = byId.get(course.course_id);
    if (current) {
      current.analytics = course;
      current.title = current.title ?? course.title ?? null;
      current.path = current.path ?? course.path ?? null;
    } else {
      byId.set(course.course_id, {
        id: course.course_id,
        title: course.title ?? null,
        path: course.path ?? null,
        analytics: course,
      });
    }
  }
  return Array.from(byId.values()).sort((a, b) =>
    (a.title || a.path || a.id).localeCompare(b.title || b.path || b.id),
  );
}

function CourseBadge({
  children,
  tone = 'blue',
}: {
  children: ReactNode;
  tone?: 'blue' | 'green' | 'gray';
}) {
  const classes =
    tone === 'green'
      ? 'bg-green-100 text-green-700'
      : tone === 'gray'
        ? 'bg-gray-100 text-gray-700'
        : 'bg-blue-100 text-blue-700';
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${classes}`}>
      {children}
    </span>
  );
}
