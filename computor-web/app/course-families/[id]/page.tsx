'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { api } from '@/src/utils/api';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';

const courseFamiliesClient = new CourseFamiliesClient();
const coursesClient = new CoursesClient();

export default function CourseFamilyDetailPage() {
  const familyId = useParams().id as string;
  const router = useRouter();
  const { canManageHierarchy: canManage, canCreateCourse } = usePermissions();
  const [confirmDelete, setConfirmDelete] = useState(false);

  const { data, loading, error } = useResource(
    async () => ({
      family: await courseFamiliesClient.getCourseFamiliesCourseFamiliesIdGet({ id: familyId }),
      courses: await coursesClient.listCoursesCoursesGet({ courseFamilyId: familyId }),
    }),
    [familyId],
  );
  const family = data?.family ?? null;
  const courses = data?.courses ?? [];
  const mayCreateCourse = family ? canCreateCourse(family.organization_id, familyId) : false;

  async function doDelete() {
    await api.del(`/course-families/${familyId}`);
    router.push('/course-families');
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Course Families', href: '/course-families' }, { label: family?.title || family?.path || 'Course Family' }]}
          title={family?.title || family?.path || 'Course Family'}
          subtitle={family && <span className="font-mono text-sm text-gray-500">{family.path}</span>}
          actions={
            <>
              {mayCreateCourse && (
                <Link href={`/courses/create?familyId=${familyId}`} className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">New Course</Link>
              )}
              {family && canManage && (
                <>
                  <Link href={`/course-families/${familyId}/edit`} className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">Edit</Link>
                  <button onClick={() => setConfirmDelete(true)} className="px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50">Delete</button>
                </>
              )}
            </>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : (
          <ScrollArea className="space-y-6">
            {family?.description && (
              <div className="bg-white border border-gray-200 rounded-lg p-5">
                <p className="text-gray-700">{family.description}</p>
              </div>
            )}

            <h2 className="text-xl font-semibold text-gray-900">
              Courses <span className="text-gray-400 font-normal">({courses.length})</span>
            </h2>
            {courses.length === 0 ? (
              <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">No courses in this family yet.</div>
            ) : (
              <div className="bg-white border border-gray-200 rounded-lg divide-y">
                {courses.map((c) => (
                  <Link key={c.id} href={`/courses/${c.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">{c.title || c.path}</div>
                      <div className="text-xs text-gray-500 font-mono">{c.path}</div>
                    </div>
                    <span className="text-gray-300">›</span>
                  </Link>
                ))}
              </div>
            )}
          </ScrollArea>
        )}
      </ListPageLayout>

      {confirmDelete && family && (
        <ConfirmDeleteDialog
          title={`Delete course family “${family.title || family.path}”?`}
          message="This permanently deletes the course family and is irreversible. It must have no courses first."
          confirmWord={family.path}
          onConfirm={doDelete}
          onClose={() => setConfirmDelete(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}
