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
import { displayName } from '@/src/utils/displayName';
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
  const familyName = displayName(family, 'Course Family');
  const mayCreateCourse = family ? canCreateCourse(family.organization_id, familyId) : false;

  async function doDelete() {
    await api.del(`/course-families/${familyId}`);
    router.push('/course-families');
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout width="narrow">
        <PageHeader
          breadcrumbs={[{ label: 'Course families', href: '/course-families' }, { label: familyName }]}
          title={familyName}
          actions={
            <>
              {mayCreateCourse && (
                <Link href={`/courses/create?familyId=${familyId}`} className="px-3 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover">New course</Link>
              )}
              {family && canManage && (
                <>
                  <Link href={`/course-families/${familyId}/edit`} className="px-3 py-2 text-sm font-medium text-body border border-rule-strong rounded-lg hover:bg-canvas">Edit</Link>
                  <button onClick={() => setConfirmDelete(true)} className="px-3 py-2 text-sm font-medium text-danger-text border border-danger-line rounded-lg hover:bg-danger-wash">Delete</button>
                </>
              )}
            </>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : (
          <ScrollArea>
            {family?.description && (
              <div className="bg-surface border border-rule rounded-lg p-5">
                <p className="text-body">{family.description}</p>
              </div>
            )}

            <h2 className="text-xl font-semibold text-fg">
              Courses <span className="text-subtle font-normal">({courses.length})</span>
            </h2>
            {courses.length === 0 ? (
              <div className="text-muted border border-dashed border-rule-strong rounded-lg p-8 text-center">No courses in this family yet.</div>
            ) : (
              <div className="bg-surface border border-rule rounded-lg divide-y">
                {courses.map((c) => (
                  <Link key={c.id} href={`/courses/${c.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-canvas">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-fg truncate">{displayName(c, 'Untitled Course')}</div>
                    </div>
                    <span className="text-faint">›</span>
                  </Link>
                ))}
              </div>
            )}
          </ScrollArea>
        )}
      </ListPageLayout>

      {confirmDelete && family && (
        <ConfirmDeleteDialog
          title={`Delete course family “${familyName}”?`}
          message="This permanently deletes the course family and is irreversible. It must have no courses first."
          confirmWord={familyName}
          onConfirm={doDelete}
          onClose={() => setConfirmDelete(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}
