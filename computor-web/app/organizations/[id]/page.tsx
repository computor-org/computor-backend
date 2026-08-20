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
import type { OrganizationGet, CourseFamilyList } from 'types/generated';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';

const organizationsClient = new OrganizationsClient();
const courseFamiliesClient = new CourseFamiliesClient();

export default function OrganizationDetailPage() {
  const orgId = useParams().id as string;
  const router = useRouter();
  const { canManageHierarchy: canManage, canCreateCourseFamily } = usePermissions();
  const [confirmDelete, setConfirmDelete] = useState(false);

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

  async function doDelete() {
    await api.del(`/organizations/${orgId}`);
    router.push('/organizations');
  }

  return (
    <AuthenticatedLayout>
      <ListPageLayout width="narrow">
        <PageHeader
          breadcrumbs={[{ label: 'Organizations', href: '/organizations' }, { label: orgName }]}
          title={orgName}
          subtitle={org && <span className="text-sm text-muted">{org.organization_type}</span>}
          actions={
            org && canManage ? (
              <>
                <Link href={`/organizations/${org.id}/edit`} className="px-3 py-2 text-sm font-medium text-body border border-rule-strong rounded-lg hover:bg-canvas">Edit</Link>
                <button onClick={() => setConfirmDelete(true)} className="px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50">Delete</button>
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
                  <Link href={`/course-families/create?organization_id=${orgId}`} className="text-sm text-blue-600 hover:underline">New course family</Link>
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

      {confirmDelete && org && (
        <ConfirmDeleteDialog
          title={`Delete organization “${orgName}”?`}
          message="This permanently deletes the organization and is irreversible. It must have no course families first."
          confirmWord={orgName}
          onConfirm={doDelete}
          onClose={() => setConfirmDelete(false)}
        />
      )}
    </AuthenticatedLayout>
  );
}
