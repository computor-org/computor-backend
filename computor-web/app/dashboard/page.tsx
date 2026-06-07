'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import type { CourseList } from '@/src/generated/types/courses';

export default function DashboardPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const { showManagement, isWorkspaceUser, isUserManager, isAdmin } = usePermissions();
  const [courses, setCourses] = useState<CourseList[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`${API_BASE_URL}/courses`);
        if (res.ok && !cancelled) setCourses(await res.json());
      } catch {
        // leave empty; the section renders an empty state
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [authLoading, isAuthenticated]);

  const actions = [
    { label: 'Browse Courses', href: '/courses', show: true },
    { label: 'Browse Examples', href: '/examples', show: true },
    { label: 'Organizations', href: '/organizations', show: showManagement },
    { label: 'Course Families', href: '/course-families', show: showManagement },
    { label: 'Workspaces', href: '/workspaces', show: isWorkspaceUser },
    { label: 'User Management', href: '/admin/users', show: isUserManager },
    { label: 'System', href: '/admin', show: isAdmin },
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
              : courses.length === 0
              ? "You're not enrolled in any courses yet."
              : `You have ${courses.length} ${courses.length === 1 ? 'course' : 'courses'}.`}
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
              ) : courses.length === 0 ? (
                <p className="text-sm text-gray-500">No courses yet.</p>
              ) : (
                <div className="space-y-2">
                  {courses.slice(0, 6).map((c) => (
                    <Link
                      key={c.id}
                      href={`/courses/${c.id}`}
                      className="block p-3 rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 transition-colors"
                    >
                      <p className="text-sm font-medium text-gray-900">{c.title || c.path}</p>
                      {c.title && c.path && <p className="text-xs text-gray-500">{c.path}</p>}
                    </Link>
                  ))}
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
