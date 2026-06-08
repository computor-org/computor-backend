'use client';

import Link from 'next/link';
import { api } from '@/src/utils/api';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import type { CourseFamilyList } from '@/src/generated/types/courses';
import type { OrganizationList } from '@/src/generated/types/organizations';

export default function CourseFamiliesPage() {
  const { canCreateCourseFamily } = usePermissions();

  const { data, loading, error } = useResource(async () => {
    const [families, orgs, courses] = await Promise.all([
      api.get<CourseFamilyList[]>('/course-families'),
      api.get<OrganizationList[]>('/organizations'),
      api.get<Array<{ course_family_id?: string | null }>>('/courses'),
    ]);
    const courseCounts: Record<string, number> = {};
    for (const c of courses) {
      if (c.course_family_id) courseCounts[c.course_family_id] = (courseCounts[c.course_family_id] ?? 0) + 1;
    }
    return { families, orgs, courseCounts };
  }, []);

  const families = data?.families ?? [];
  const orgs = data?.orgs ?? [];
  const courseCounts = data?.courseCounts ?? {};
  const orgLabel = (id: string) => {
    const o = orgs.find((x) => x.id === id);
    return o ? o.title || o.path : id;
  };

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <PageHeader
          breadcrumbs={[{ label: 'Course Families' }]}
          title="Course Families"
          subtitle="A course family groups related courses within an organization."
          actions={
            canCreateCourseFamily() ? (
              <Link href="/course-families/create" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
                New Course Family
              </Link>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : families.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">No course families yet.</div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg divide-y">
            {families.map((f) => (
              <Link key={f.id} href={`/course-families/${f.id}`} className="block px-4 py-3 hover:bg-gray-50">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium text-gray-900">{f.title || f.path}</div>
                  <span className="shrink-0 text-xs text-gray-500">
                    {courseCounts[f.id] ?? 0} {(courseCounts[f.id] ?? 0) === 1 ? 'course' : 'courses'}
                  </span>
                </div>
                <div className="text-xs text-gray-500">{f.path} · {orgLabel(f.organization_id)}</div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
