'use client';

import Link from 'next/link';
import { api } from '@/src/utils/api';
import { useAuth } from '@/src/contexts/AuthContext';
import { useResource } from '@/src/hooks/useResource';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import PageHeader from '@/src/components/PageHeader';
import ErrorBanner from '@/src/components/ErrorBanner';
import Forbidden from '@/src/components/Forbidden';
import type { ExampleRepositoryList } from 'types/generated';

export default function ExampleRepositoriesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { canManageHierarchy: canManage } = usePermissions();

  const { data, loading, error } = useResource(() => api.get<ExampleRepositoryList[]>('/example-repositories?limit=200'), [], { enabled: canManage });
  const repos = data ?? [];

  if (!authLoading && isAuthenticated && !canManage) {
    return <Forbidden message="You do not have access to example repositories." />;
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <PageHeader
          breadcrumbs={[{ label: 'Example Repositories' }]}
          title="Example Repositories"
          subtitle="Storage backends that hold examples. Upload examples into a MinIO repository."
          actions={
            <Link href="/example-repositories/create" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
              New repository
            </Link>
          }
        />

        <ErrorBanner>{error}</ErrorBanner>

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
