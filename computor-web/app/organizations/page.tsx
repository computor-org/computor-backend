'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import type { OrganizationList } from '@/src/generated/types/organizations';

export default function OrganizationsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canCreateOrganization } = usePermissions();
  const [orgs, setOrgs] = useState<OrganizationList[]>([]);
  const [familyCounts, setFamilyCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [orgRes, famRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/organizations`),
        apiFetch(`${API_BASE_URL}/course-families`),
      ]);
      if (!orgRes.ok) throw new Error('Failed to load organizations');
      setOrgs(await orgRes.json());
      if (famRes.ok) {
        const fams: Array<{ organization_id: string }> = await famRes.json();
        const counts: Record<string, number> = {};
        for (const f of fams) counts[f.organization_id] = (counts[f.organization_id] ?? 0) + 1;
        setFamilyCounts(counts);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    load();
  }, [authLoading, isAuthenticated, load]);

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <Breadcrumbs items={[{ label: 'Organizations' }]} />
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Organizations</h1>
            <p className="mt-2 text-gray-600">The top of the hierarchy: organizations contain course families.</p>
          </div>
          {canCreateOrganization && (
            <Link href="/organizations/create" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
              New Organization
            </Link>
          )}
        </div>

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

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
