'use client';

import Link from 'next/link';
import { api } from '@/src/utils/api';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import type { OrganizationList } from '@/src/generated/types/organizations';

export default function OrganizationsPage() {
  const { canCreateOrganization } = usePermissions();

  const { data, loading, error } = useResource(async () => {
    const [orgs, fams] = await Promise.all([
      api.get<OrganizationList[]>('/organizations'),
      api.get<Array<{ organization_id: string }>>('/course-families'),
    ]);
    const familyCounts: Record<string, number> = {};
    for (const f of fams) familyCounts[f.organization_id] = (familyCounts[f.organization_id] ?? 0) + 1;
    return { orgs, familyCounts };
  }, []);

  const orgs = data?.orgs ?? [];
  const familyCounts = data?.familyCounts ?? {};

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <PageHeader
          breadcrumbs={[{ label: 'Organizations' }]}
          title="Organizations"
          subtitle="The top of the hierarchy: organizations contain course families."
          actions={
            canCreateOrganization ? (
              <Link href="/organizations/create" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
                New Organization
              </Link>
            ) : undefined
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : orgs.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
            No organizations yet{canCreateOrganization ? ' — create one to get started.' : '.'}
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg divide-y">
            {orgs.map((o) => (
              <div key={o.id} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                <Link href={`/organizations/${o.id}`} className="min-w-0 group flex-1">
                  <div className="text-sm font-medium text-gray-900 truncate group-hover:text-blue-600">{o.title || o.path}</div>
                  <div className="text-xs text-gray-500">{o.path} · {o.organization_type}</div>
                </Link>
                <Link href={`/course-families?organization_id=${o.id}`} className="text-sm text-blue-600 hover:underline whitespace-nowrap ml-4">
                  {familyCounts[o.id] ?? 0} course {(familyCounts[o.id] ?? 0) === 1 ? 'family' : 'families'} →
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
