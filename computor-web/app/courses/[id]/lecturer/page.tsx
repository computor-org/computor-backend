'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import PageHeader from '@/src/components/PageHeader';
import type { CourseGet } from 'types/generated';

const SECTIONS = [
  {
    slug: 'assignments',
    title: 'Assignments',
    desc: 'Units, assignments & example deployment status',
    icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10',
  },
  {
    slug: 'students',
    title: 'Students',
    desc: 'Student progress, grading & activity',
    icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
  },
  {
    slug: 'analytics',
    title: 'Analytics',
    desc: 'Progress & performance overview',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  },
];

export default function LecturerViewPage() {
  const courseId = useParams().id as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [course, setCourse] = useState<CourseGet | null>(null);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`${API_BASE_URL}/courses/${courseId}`);
        if (!cancelled && res.ok) setCourse(await res.json());
      } catch {
        /* header is best-effort */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [courseId, authLoading, isAuthenticated]);

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <PageHeader
          breadcrumbs={[
            { label: 'Courses', href: '/courses' },
            { label: course?.title || course?.path || 'Course', href: `/courses/${courseId}` },
            { label: 'Lecturer View' },
          ]}
          title="Lecturer View"
          subtitle={course ? <span className="text-sm text-gray-500 font-mono">{course.path}</span> : undefined}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {SECTIONS.map((s) => (
            <Link
              key={s.slug}
              href={`/courses/${courseId}/lecturer/${s.slug}`}
              className="p-5 bg-white border-2 border-gray-200 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all flex items-start gap-4"
            >
              <svg className="h-8 w-8 text-blue-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={s.icon} />
              </svg>
              <div>
                <h3 className="font-semibold text-gray-900">{s.title}</h3>
                <p className="text-sm text-gray-500 mt-0.5">{s.desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </AuthenticatedLayout>
  );
}
