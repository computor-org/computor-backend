'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import NotFound from '@/src/components/NotFound';
import type { ExampleRepositoryList } from 'types/generated';

export default function ExampleRepositoriesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [repos, setRepos] = useState<ExampleRepositoryList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`${API_BASE_URL}/example-repositories?limit=200`);
      if (!res.ok) throw new Error('Failed to load example repositories');
      setRepos(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    load();
  }, [authLoading, isAuthenticated, canManage, load]);

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="You do not have access to example repositories." />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <Breadcrumbs items={[{ label: 'Example Repositories' }]} />
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Example Repositories</h1>
            <p className="mt-1 text-gray-600">Storage backends that hold examples. Upload examples into a MinIO repository.</p>
          </div>
          <Link href="/example-repositories/create" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            New repository
          </Link>
        </div>

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : repos.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
            No example repositories yet. Create a MinIO repository to upload examples into.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {repos.map((r) => {
              const uploadable = r.source_type === 'minio' || r.source_type === 's3';
              return (
                <Link key={r.id} href={`/example-repositories/${r.id}`} className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-all">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-lg font-semibold text-gray-900 truncate">{r.name}</h3>
                    <span className={`shrink-0 px-2 py-0.5 text-xs font-medium rounded ${uploadable ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {r.source_type}
                    </span>
                  </div>
                  {r.description && <p className="mt-1 text-sm text-gray-600 line-clamp-2">{r.description}</p>}
                  <p className="mt-3 text-xs text-gray-400 font-mono truncate">{r.source_url}</p>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
