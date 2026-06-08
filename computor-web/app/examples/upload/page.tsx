'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import NotFound from '@/src/components/NotFound';
import { discoverExamplesInZip, type DiscoveredExample } from '@/src/utils/exampleZip';
import type { ExampleRepositoryList } from 'types/generated';

const DIR_OK = /^[a-zA-Z0-9._-]+$/;

interface UploadRow extends DiscoveredExample {
  status: 'pending' | 'uploading' | 'ok' | 'error';
  message?: string;
}

function UploadInner() {
  const router = useRouter();
  const params = useSearchParams();
  const initialRepo = params.get('repository') || '';
  const forcedDirectory = params.get('directory') || '';

  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [repos, setRepos] = useState<ExampleRepositoryList[]>([]);
  const [repoId, setRepoId] = useState(initialRepo);
  const [rows, setRows] = useState<UploadRow[]>([]);
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiFetch(`${API_BASE_URL}/example-repositories?limit=200`);
      if (res.ok) {
        const all: ExampleRepositoryList[] = await res.json();
        const uploadable = all.filter((r) => r.source_type === 'minio' || r.source_type === 's3');
        setRepos(uploadable);
        if (!initialRepo && uploadable.length === 1) setRepoId(uploadable[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load repositories');
    }
  }, [initialRepo]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    load();
  }, [authLoading, isAuthenticated, canManage, load]);

  async function onPickZip(file: File | undefined) {
    if (!file) return;
    setParsing(true);
    setParseError(null);
    setRows([]);
    try {
      const discovered = await discoverExamplesInZip(file);
      // "Upload new version" targets a specific directory: when a single example
      // is discovered and a directory is forced, honour it.
      const adjusted =
        forcedDirectory && discovered.length === 1 ? [{ ...discovered[0], directory: forcedDirectory }] : discovered;
      setRows(adjusted.map((d) => ({ ...d, status: 'pending' })));
    } catch (e) {
      setParseError(e instanceof Error ? e.message : 'Could not read the zip');
    } finally {
      setParsing(false);
    }
  }

  async function runUpload() {
    if (!repoId) return;
    setUploading(true);
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, status: 'uploading', message: undefined } : r)));
      try {
        const res = await apiFetch(`${API_BASE_URL}/examples/upload`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ repository_id: repoId, directory: row.directory, files: row.files }),
        });
        if (!res.ok) throw new Error((await res.text()) || `Upload failed (${res.status})`);
        const v = await res.json();
        setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, status: 'ok', message: `v${v.version_tag ?? ''}` } : r)));
      } catch (e) {
        setRows((rs) =>
          rs.map((r, idx) => (idx === i ? { ...r, status: 'error', message: e instanceof Error ? e.message : 'Upload failed' } : r)),
        );
      }
    }
    setUploading(false);
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="You do not have access to examples." backLink="/examples" backText="Back" />
      </AuthenticatedLayout>
    );
  }

  const dirsValid = rows.length > 0 && rows.every((r) => DIR_OK.test(r.directory));
  const allDone = rows.length > 0 && rows.every((r) => r.status === 'ok' || r.status === 'error');

  return (
    <AuthenticatedLayout>
      <div className="p-6 max-w-2xl">
        <Breadcrumbs items={[{ label: 'Examples', href: '/examples' }, { label: 'Upload' }]} />
        <h1 className="text-2xl font-bold text-gray-900">Upload examples</h1>
        <p className="mt-1 text-gray-600">
          Choose a repository and a .zip of one example (a root <code className="font-mono">meta.yaml</code>) or several
          (each in its own folder with a <code className="font-mono">meta.yaml</code>).
        </p>

        <div className="mt-6 bg-white border border-gray-200 rounded-lg p-6 space-y-4">
          {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Repository</label>
            {repos.length === 0 ? (
              <p className="text-sm text-gray-500">
                No uploadable (MinIO/S3) repository.{' '}
                <Link href="/example-repositories/create" className="text-blue-600 hover:underline">Create one first</Link>.
              </p>
            ) : (
              <select
                value={repoId}
                onChange={(e) => setRepoId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              >
                <option value="">— select a repository —</option>
                {repos.map((r) => (
                  <option key={r.id} value={r.id}>{r.name} ({r.source_type})</option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Zip file</label>
            <input
              type="file"
              accept=".zip,application/zip"
              onChange={(e) => onPickZip(e.target.files?.[0])}
              className="block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 file:text-sm file:font-medium hover:file:bg-blue-100"
            />
          </div>

          {parsing && <div className="text-sm text-gray-500">Reading zip…</div>}
          {parseError && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{parseError}</div>}

          {rows.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-medium text-gray-500">Discovered {rows.length} example{rows.length > 1 ? 's' : ''}</div>
              {rows.map((r, i) => (
                <div key={i} className="flex items-center gap-3 border border-gray-200 rounded-lg px-3 py-2">
                  <input
                    value={r.directory}
                    disabled={uploading || r.status === 'ok'}
                    onChange={(e) => setRows((rs) => rs.map((x, idx) => (idx === i ? { ...x, directory: e.target.value } : x)))}
                    className={`flex-1 px-2 py-1 border rounded text-sm font-mono ${DIR_OK.test(r.directory) ? 'border-gray-300' : 'border-red-400'}`}
                  />
                  <span className="text-xs text-gray-400 shrink-0">{r.fileCount} files</span>
                  <span
                    className={`text-xs shrink-0 w-40 truncate text-right ${
                      r.status === 'ok' ? 'text-green-600' : r.status === 'error' ? 'text-red-600' : r.status === 'uploading' ? 'text-amber-600' : 'text-gray-400'
                    }`}
                    title={r.message}
                  >
                    {r.status === 'pending' ? 'ready' : r.status === 'uploading' ? 'uploading…' : r.status === 'ok' ? `uploaded ${r.message ?? ''}` : r.message}
                  </span>
                </div>
              ))}
              {!dirsValid && (
                <p className="text-xs text-red-600">Directory names may only contain letters, numbers, dots, dashes and underscores.</p>
              )}
            </div>
          )}
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button onClick={() => router.push('/examples')} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
            {allDone ? 'Done' : 'Cancel'}
          </button>
          <button
            onClick={runUpload}
            disabled={uploading || rows.length === 0 || !dirsValid || !repoId || allDone}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? 'Uploading…' : `Upload ${rows.length || ''}`}
          </button>
        </div>
      </div>
    </AuthenticatedLayout>
  );
}

export default function ExampleUploadPage() {
  return (
    <Suspense fallback={<AuthenticatedLayout><div className="p-6 text-gray-500">Loading…</div></AuthenticatedLayout>}>
      <UploadInner />
    </Suspense>
  );
}
