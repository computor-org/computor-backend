'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import type { ExampleRepositoryList } from 'types/generated';

const inputCls =
  'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';

interface CreateState {
  open: boolean;
  saving: boolean;
  error: string | null;
  name: string;
  sourceType: 'minio' | 's3' | 'git';
  sourceUrl: string;
  description: string;
}
const emptyCreate: CreateState = {
  open: false,
  saving: false,
  error: null,
  name: '',
  sourceType: 'minio',
  sourceUrl: 'computor-storage',
  description: '',
};

export default function ExampleRepositoriesPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [repos, setRepos] = useState<ExampleRepositoryList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [create, setCreate] = useState<CreateState>(emptyCreate);

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

  async function handleCreate() {
    setCreate((c) => ({ ...c, saving: true, error: null }));
    try {
      const res = await apiFetch(`${API_BASE_URL}/example-repositories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: create.name.trim(),
          description: create.description.trim() || null,
          source_type: create.sourceType,
          source_url: create.sourceUrl.trim(),
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Create failed (${res.status})`);
      setCreate(emptyCreate);
      await load();
    } catch (e) {
      setCreate((c) => ({ ...c, saving: false, error: e instanceof Error ? e.message : 'Create failed' }));
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="You do not have access to example management." />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Examples</h1>
            <p className="mt-1 text-gray-600">
              Example repositories. Upload examples into a MinIO repository, then assign them to assignments from a course.
            </p>
          </div>
          <button
            onClick={() => setCreate({ ...emptyCreate, open: true })}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            New repository
          </button>
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
                <Link
                  key={r.id}
                  href={`/examples/${r.id}`}
                  className="bg-white border border-gray-200 rounded-lg p-5 hover:shadow-md transition-all"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-lg font-semibold text-gray-900 truncate">{r.name}</h3>
                    <span
                      className={`shrink-0 px-2 py-0.5 text-xs font-medium rounded ${
                        uploadable ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {r.source_type}
                    </span>
                  </div>
                  {r.description && <p className="mt-1 text-sm text-gray-600 line-clamp-2">{r.description}</p>}
                  <p className="mt-3 text-xs text-gray-400 font-mono truncate">{r.source_url}</p>
                  {!uploadable && (
                    <p className="mt-1 text-xs text-gray-400">Read-only here (synced via git).</p>
                  )}
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {create.open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">New example repository</h2>
              {create.error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{create.error}</div>
              )}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Name <span className="text-red-500">*</span>
                </label>
                <input value={create.name} onChange={(e) => setCreate((c) => ({ ...c, name: e.target.value }))} placeholder="Course examples" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Storage</label>
                <select
                  value={create.sourceType}
                  onChange={(e) => setCreate((c) => ({ ...c, sourceType: e.target.value as CreateState['sourceType'] }))}
                  className={inputCls}
                >
                  <option value="minio">MinIO (uploadable)</option>
                  <option value="s3">S3 (uploadable)</option>
                  <option value="git">Git (read-only — synced via push)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {create.sourceType === 'git' ? 'Git URL' : 'Bucket (source URL)'} <span className="text-red-500">*</span>
                </label>
                <input value={create.sourceUrl} onChange={(e) => setCreate((c) => ({ ...c, sourceUrl: e.target.value }))} className={inputCls} />
                {create.sourceType !== 'git' && (
                  <p className="mt-1 text-xs text-gray-400">First path segment is the bucket (default: computor-storage).</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Description</label>
                <textarea value={create.description} onChange={(e) => setCreate((c) => ({ ...c, description: e.target.value }))} rows={2} className={inputCls} />
              </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2">
              <button onClick={() => setCreate(emptyCreate)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={create.saving || !create.name.trim() || !create.sourceUrl.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {create.saving ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AuthenticatedLayout>
  );
}
