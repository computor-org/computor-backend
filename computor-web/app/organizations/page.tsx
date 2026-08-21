'use client';

import Link from 'next/link';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import ListPageLayout, { ScrollArea, ListLoading } from '@/src/components/ListPageLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import { displayName } from '@/src/utils/displayName';
import { OrganizationsClient } from '@/src/generated/clients/OrganizationsClient';
import { CourseFamiliesClient } from '@/src/generated/clients/CourseFamiliesClient';

const organizationsClient = new OrganizationsClient();
const courseFamiliesClient = new CourseFamiliesClient();

export default function OrganizationsPage() {
  const { canCreateOrganization } = usePermissions();

  const { data, loading, error } = useResource(async () => {
    const [orgs, fams] = await Promise.all([
      organizationsClient.listOrganizationsOrganizationsGet({}),
      courseFamiliesClient.listCourseFamiliesCourseFamiliesGet({}),
    ]);
    const familyCounts: Record<string, number> = {};
    for (const f of fams) familyCounts[f.organization_id] = (familyCounts[f.organization_id] ?? 0) + 1;
    return { orgs, familyCounts };
  }, []);

  const orgs = data?.orgs ?? [];
  const familyCounts = data?.familyCounts ?? {};

  return (
    <AuthenticatedLayout>
      <ListPageLayout>
        <PageHeader
          breadcrumbs={[{ label: 'Organizations' }]}
          title="Organizations"
          subtitle="The top of the hierarchy: organizations contain course families."
          actions={
            canCreateOrganization ? (
              <Link href="/organizations/create" className="px-4 py-2 bg-accent text-on-accent rounded-lg text-sm font-medium hover:bg-accent-hover">
                New Organization
              </Link>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <ListLoading>Loading…</ListLoading>
        ) : orgs.length === 0 ? (
          <div className="text-muted border border-dashed border-rule-strong rounded-lg p-8 text-center">
            No organizations yet{canCreateOrganization ? ' — create one to get started.' : '.'}
          </div>
        ) : (
          <ScrollArea spacing="rows">
            {orgs.map((o) => (
              <div key={o.id} className="flex items-center justify-between gap-4 bg-surface border border-rule rounded-lg p-4 hover:border-accent-line hover:shadow-sm transition-all">
                <Link href={`/organizations/${o.id}`} className="min-w-0 group flex-1">
                  <div className="text-sm font-medium text-fg truncate group-hover:text-accent-text">{displayName(o, 'Untitled Organization')}</div>
                  <div className="text-xs text-muted">{o.organization_type}</div>
                </Link>
                <Link href={`/course-families?organization_id=${o.id}`} className="text-sm text-accent-text hover:underline whitespace-nowrap">
                  {familyCounts[o.id] ?? 0} course {(familyCounts[o.id] ?? 0) === 1 ? 'family' : 'families'} →
                </Link>
              </div>
            ))}
          </ScrollArea>
        )}
      </ListPageLayout>
    </AuthenticatedLayout>
  );
}
