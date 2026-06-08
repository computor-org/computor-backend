'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import type { OrganizationGet, CourseFamilyList } from 'types/generated';

export default function OrganizationDetailPage() {
  const orgId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager, canCreateCourseFamily } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [org, setOrg] = useState<OrganizationGet | null>(null);
  const [families, setFamilies] = useState<CourseFamilyList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [oRes, fRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/organizations/${orgId}`),
        apiFetch(`${API_BASE_URL}/course-families?organization_id=${orgId}`),
      ]);
      if (!oRes.ok) throw new Error('Failed to load organization');
      setOrg(await oRes.json());
      if (fRes.ok) setFamilies(await fRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    load();
  }, [authLoading, isAuthenticated, load]);

  async function remove() {
    if (!confirm('Delete this organization? Its course families must be removed first.')) return;
    const res = await apiFetch(`${API_BASE_URL}/organizations/${orgId}`, { method: 'DELETE' });
    if (res.ok) router.push('/organizations');
    else setError((await res.text()) || 'Delete failed');
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <Breadcrumbs items={[{ label: 'Organizations', href: '/organizations' }, { label: org?.title || org?.path || 'Organization' }]} />

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : org ? (
          <>
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">{org.title || org.path}</h1>
                <p className="mt-1 text-sm text-gray-500 font-mono">{org.path} · {org.organization_type}</p>
              </div>
              {canManage && (
                <div className="flex items-center gap-2">
                  <Link href={`/organizations/${org.id}/edit`} className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
                    Edit
                  </Link>
                  <button onClick={remove} className="px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50">
                    Delete
                  </button>
                </div>
              )}
            </div>

            {org.description && (
              <div className="bg-white border border-gray-200 rounded-lg p-5">
                <p className="text-gray-700">{org.description}</p>
              </div>
            )}

            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xl font-semibold text-gray-900">
                  Course Families <span className="text-gray-400 font-normal">({families.length})</span>
                </h2>
                {canCreateCourseFamily(orgId) && (
                  <Link href={`/course-families/create?organization_id=${orgId}`} className="text-sm text-blue-600 hover:underline">
                    New course family
                  </Link>
                )}
              </div>
              {families.length === 0 ? (
                <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">No course families yet.</div>
              ) : (
                <div className="bg-white border border-gray-200 rounded-lg divide-y">
                  {families.map((f) => (
                    <Link key={f.id} href={`/course-families/${f.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">{f.title || f.path}</div>
                        <div className="text-xs text-gray-400 font-mono truncate">{f.path}</div>
                      </div>
                      <span className="text-gray-300">›</span>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </AuthenticatedLayout>
  );
}
