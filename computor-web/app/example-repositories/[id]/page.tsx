'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import NotFound from '@/src/components/NotFound';
import type { ExampleRepositoryGet, ExampleList } from 'types/generated';

export default function ExampleRepositoryDetailPage() {
  const repoId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [repo, setRepo] = useState<ExampleRepositoryGet | null>(null);
  const [examples, setExamples] = useState<ExampleList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rRes, eRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/example-repositories/${repoId}`),
        apiFetch(`${API_BASE_URL}/examples?repository_id=${repoId}&limit=500`),
      ]);
      if (!rRes.ok) throw new Error('Failed to load repository');
      setRepo(await rRes.json());
      if (eRes.ok) setExamples(await eRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [repoId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    load();
  }, [authLoading, isAuthenticated, canManage, load]);

  async function remove() {
    if (!confirm('Delete this repository? Examples it contains must be removed first.')) return;
    const res = await apiFetch(`${API_BASE_URL}/example-repositories/${repoId}`, { method: 'DELETE' });
    if (res.ok) router.push('/example-repositories');
    else setError((await res.text()) || 'Delete failed');
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="You do not have access to example repositories." backLink="/example-repositories" backText="Back" />
      </AuthenticatedLayout>
    );
  }

  const uploadable = repo?.source_type === 'minio' || repo?.source_type === 's3';

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <Breadcrumbs items={[{ label: 'Example Repositories', href: '/example-repositories' }, { label: repo?.name || 'Repository' }]} />

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : repo ? (
          <>
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">{repo.name}</h1>
                <p className="mt-1 text-sm text-gray-500 font-mono">{repo.source_type} · {repo.source_url}</p>
              </div>
              <div className="flex items-center gap-2">
                {uploadable && (
                  <Link href={`/examples/upload?repository=${repo.id}`} className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
                    Upload examples
                  </Link>
                )}
                <Link href={`/example-repositories/${repo.id}/edit`} className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
                  Edit
                </Link>
                <button onClick={remove} className="px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50">
                  Delete
                </button>
              </div>
            </div>

            {repo.description && (
              <div className="bg-white border border-gray-200 rounded-lg p-5">
                <p className="text-gray-700">{repo.description}</p>
              </div>
            )}

            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">
                Examples <span className="text-gray-400 font-normal">({examples.length})</span>
              </h2>
              {examples.length === 0 ? (
                <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
                  No examples yet.{uploadable ? ' Upload a zip containing one or more examples (each with a meta.yaml).' : ''}
                </div>
              ) : (
                <div className="bg-white border border-gray-200 rounded-lg divide-y">
                  {examples.map((ex) => (
                    <Link key={ex.id} href={`/examples/${ex.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-900 truncate">{ex.title || ex.directory}</div>
                        <div className="text-xs text-gray-400 font-mono truncate">{ex.identifier}</div>
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
