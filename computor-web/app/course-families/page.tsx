'use client';

import Link from 'next/link';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';

const organizationsClient = new OrganizationsClient();
const courseFamiliesClient = new CourseFamiliesClient();
const coursesClient = new CoursesClient();

export default function CourseFamiliesPage() {
  const { canCreateCourseFamily } = usePermissions();

  const { data, loading, error } = useResource(async () => {
    const [families, orgs, courses] = await Promise.all([
      courseFamiliesClient.listCourseFamiliesCourseFamiliesGet({}),
      organizationsClient.listOrganizationsOrganizationsGet({}),
      coursesClient.listCoursesCoursesGet({}),
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
      <ListPageLayout>
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
          <ListLoading>Loading…</ListLoading>
        ) : families.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">No course families yet.</div>
        ) : (
          <ScrollArea className="space-y-3">
            {families.map((f) => (
              <Link key={f.id} href={`/course-families/${f.id}`} className="block bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-500 hover:shadow-sm transition-all">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-medium text-gray-900">{f.title || f.path}</div>
                  <span className="shrink-0 text-xs text-gray-500">
                    {courseCounts[f.id] ?? 0} {(courseCounts[f.id] ?? 0) === 1 ? 'course' : 'courses'}
                  </span>
                </div>
                <div className="text-xs text-gray-500">{f.path} · {orgLabel(f.organization_id)}</div>
              </Link>
            ))}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
