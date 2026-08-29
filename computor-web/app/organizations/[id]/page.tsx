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
import ConfirmDeleteDialog from '@/src/components/ConfirmDeleteDialog';
import CascadeDeletePreview from '@/src/components/CascadeDeletePreview';
import Button, { ButtonLink } from '@/src/components/ui/Button';
import { displayName } from '@/src/utils/displayName';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';

const organizationsClient = new OrganizationsClient();
const courseFamiliesClient = new CourseFamiliesClient();

export default function OrganizationDetailPage() {
  const orgId = useParams().id as string;
  const router = useRouter();
  const { refreshPermissions } = useAuth();
  const { canManageHierarchy: canManage, canCreateCourseFamily, canDeleteOrganization } = usePermissions();

  const { data, loading, error } = useResource(
    async () => ({
      org: await organizationsClient.getOrganizationsOrganizationsIdGet({ id: orgId }),
      families: await courseFamiliesClient.listCourseFamiliesCourseFamiliesGet({ organizationId: orgId }),
    }),
    [orgId],
  );
  const org = data?.org ?? null;
  const families = data?.families ?? [];
  const orgName = displayName(org, 'Organization');

  // Preview (dry run) first, then the real delete behind the typed-path dialog.
  // Deleting removes the caller's own _owner role, so the cached scopes are
  // refreshed before navigating — otherwise the list would still offer it.
  const del = useCascadeDelete(
    () => organizationsClient.deleteOrganizationEndpointOrganizationsOrganizationIdDelete({ organizationId: orgId, dryRun: true }),
    () => organizationsClient.deleteOrganizationEndpointOrganizationsOrganizationIdDelete({ organizationId: orgId, dryRun: false }),
    async () => {
      await refreshPermissions();
      router.push('/organizations');
    },
  );

  return (
    <AuthenticatedLayout>
      <ListPageLayout width="narrow">
        <PageHeader
          breadcrumbs={[{ label: 'Organizations', href: '/organizations' }, { label: orgName }]}
          title={orgName}
          subtitle={org && <span className="text-sm text-muted">{org.organization_type}</span>}
          actions={
            org ? (
              <>
                {canManage && (
                  <ButtonLink href={`/organizations/${org.id}/edit`} variant="secondary">Edit</ButtonLink>
                )}
                {canDeleteOrganization(orgId) && (
                  <Button variant="dangerGhost" onClick={del.begin} loading={del.opening} loadingLabel="Delete">
                    Delete
                  </Button>
                )}
              </>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : org ? (
          <ScrollArea>
            {org.description && (
              <div className="bg-surface border border-rule rounded-lg p-5">
                <p className="text-body">{org.description}</p>
              </div>
            )}

            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xl font-semibold text-fg">
                  Course Families <span className="text-subtle font-normal">({families.length})</span>
                </h2>
                {canCreateCourseFamily(orgId) && (
                  <Link href={`/course-families/create?organization_id=${orgId}`} className="text-sm text-accent-text hover:underline">New course family</Link>
                )}
              </div>
              {families.length === 0 ? (
                <div className="text-muted border border-dashed border-rule-strong rounded-lg p-8 text-center">No course families yet.</div>
              ) : (
                <div className="bg-surface border border-rule rounded-lg divide-y">
                  {families.map((f) => (
                    <Link key={f.id} href={`/course-families/${f.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-canvas">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-fg truncate">{displayName(f, 'Untitled Course Family')}</div>
                      </div>
                      <span className="text-faint">›</span>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>
        ) : null}
      </ListPageLayout>

      {del.preview && org && (
        <ConfirmDeleteDialog
          title={`Delete organization “${orgName}”?`}
          message="This permanently deletes the organization and is irreversible. It must have no course families first."
          confirmWord={org.path}
          preview={<CascadeDeletePreview result={del.preview} />}
          blockedReason={del.preview.blocked_reason}
          onConfirm={del.confirm}
          onClose={del.close}
        />
      )}
    </AuthenticatedLayout>
  );
}
