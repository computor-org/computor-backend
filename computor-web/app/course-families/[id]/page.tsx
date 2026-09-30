'use client';

import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import { useCascadeDelete } from '@/src/hooks/useCascadeDelete';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Badge from '@/src/components/Badge';
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import CascadeDeletePreview from '@/src/components/CascadeDeletePreview';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import { displayName } from '@/src/utils/displayName';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';
import { CoursesClient } from '@/src/generated/clients/CoursesClient';

const courseFamiliesClient = new CourseFamiliesClient();
const coursesClient = new CoursesClient();

export default function CourseFamilyDetailPage() {
  const familyId = useParams().id as string;
  const router = useRouter();
  const { refreshPermissions } = useAuth();
  const { canManageHierarchy: canManage, canCreateCourse, canDeleteCourseFamily } = usePermissions();

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

  // Preview (dry run) first, then the real delete behind the typed-path dialog.
  // Deleting removes the caller's own _owner role, so the cached scopes are
  // refreshed before navigating — otherwise the list would still offer it.
  const del = useCascadeDelete(
    () => courseFamiliesClient.deleteCourseFamilyEndpointCourseFamiliesCourseFamilyIdDelete({ courseFamilyId: familyId, dryRun: true }),
    () => courseFamiliesClient.deleteCourseFamilyEndpointCourseFamiliesCourseFamilyIdDelete({ courseFamilyId: familyId, dryRun: false }),
    async () => {
      await refreshPermissions();
      router.push('/course-families');
    },
  );

  return (
    <AuthenticatedLayout>
      <ListPageLayout width="narrow">
        <PageHeader
          breadcrumbs={[{ label: 'Course families', href: '/course-families' }, { label: familyName }]}
          title={familyName}
          actions={
            <>
              {mayCreateCourse && (
                <ButtonLink href={`/courses/create?familyId=${familyId}`}>New course</ButtonLink>
              )}
              {family && canManage && (
                <ButtonLink href={`/course-families/${familyId}/edit`} variant="secondary">Edit</ButtonLink>
              )}
              {family && canDeleteCourseFamily(familyId) && (
                <Button variant="dangerGhost" onClick={del.begin} loading={del.opening} loadingLabel="Delete">
                  Delete
                </Button>
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
                    <div className="min-w-0 flex items-center gap-2">
                      <div className="text-sm font-medium text-fg truncate">{displayName(c, 'Untitled Course')}</div>
                      {c.archived_at && <Badge tone="muted">Archived</Badge>}
                    </div>
                    <span className="text-faint">›</span>
                  </Link>
                ))}
              </div>
            )}
          </ScrollArea>
        )}
      </ListPageLayout>

      {del.preview && family && (
        <ConfirmDeleteDialog
          title={`Delete course family “${familyName}”?`}
          message="This permanently deletes the course family and is irreversible. It must have no courses first."
          confirmWord={family.path}
          preview={<CascadeDeletePreview result={del.preview} />}
          blockedReason={del.preview.blocked_reason}
          onConfirm={del.confirm}
          onClose={del.close}
        />
      )}
    </AuthenticatedLayout>
  );
}
