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
import type { ExampleGet, ExampleVersionList } from 'types/generated';

export default function ExampleDetailPage() {
  const exampleId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [example, setExample] = useState<ExampleGet | null>(null);
  const [versions, setVersions] = useState<ExampleVersionList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [eRes, vRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/examples/${exampleId}`),
        apiFetch(`${API_BASE_URL}/examples/${exampleId}/versions?limit=200`),
      ]);
      if (!eRes.ok) throw new Error('Failed to load example');
      setExample(await eRes.json());
      if (vRes.ok) setVersions(await vRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [exampleId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    load();
  }, [authLoading, isAuthenticated, canManage, load]);

  async function remove() {
    if (!confirm('Delete this example and all its versions?')) return;
    const res = await apiFetch(`${API_BASE_URL}/examples/${exampleId}`, { method: 'DELETE' });
    if (res.ok) router.push('/examples');
    else setError((await res.text()) || 'Delete failed');
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="You do not have access to examples." backLink="/examples" backText="Back" />
      </AuthenticatedLayout>
    );
  }

  const repoId = example?.example_repository_id;
  const uploadHref = example
    ? `/examples/upload?repository=${repoId ?? ''}&directory=${encodeURIComponent(example.directory)}`
    : '/examples/upload';

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <Breadcrumbs items={[{ label: 'Examples', href: '/examples' }, { label: example?.title || example?.directory || 'Example' }]} />

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : example ? (
          <>
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">{example.title || example.directory}</h1>
                <p className="mt-1 text-sm text-gray-400 font-mono">{example.identifier}</p>
              </div>
              <div className="flex items-center gap-2">
                <Link href={uploadHref} className="px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">
                  Upload new version
                </Link>
                <button onClick={remove} className="px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50">
                  Delete
                </button>
              </div>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
              <div>
                <dt className="text-gray-500">Directory</dt>
                <dd className="text-gray-900 font-mono">{example.directory}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Repository</dt>
                <dd className="text-gray-900">
                  {repoId ? (
                    <Link href={`/example-repositories/${repoId}`} className="text-blue-600 hover:underline">View repository</Link>
                  ) : '—'}
                </dd>
              </div>
              {example.description && (
                <div className="sm:col-span-2">
                  <dt className="text-gray-500">Description</dt>
                  <dd className="text-gray-900">{example.description}</dd>
                </div>
              )}
              {(example.tags || []).length > 0 && (
                <div className="sm:col-span-2">
                  <dt className="text-gray-500">Tags</dt>
                  <dd className="flex flex-wrap gap-1.5 mt-1">
                    {(example.tags || []).map((t) => (
                      <span key={t} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">{t}</span>
                    ))}
                  </dd>
                </div>
              )}
            </div>

            <div>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">
                Versions <span className="text-gray-400 font-normal">({versions.length})</span>
              </h2>
              {versions.length === 0 ? (
                <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-6 text-center">No versions.</div>
              ) : (
                <div className="bg-white border border-gray-200 rounded-lg divide-y">
                  {versions.map((v) => (
                    <div key={v.id} className="flex items-center justify-between px-4 py-3">
                      <div className="font-mono text-sm text-gray-900">v{v.version_tag}</div>
                      <div className="text-sm text-gray-500 truncate flex-1 px-4">{v.title || ''}</div>
                      <div className="text-xs text-gray-400">{v.created_at ? new Date(v.created_at).toLocaleDateString() : ''}</div>
                    </div>
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
