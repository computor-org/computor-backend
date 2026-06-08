'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import NotFound from '@/src/components/NotFound';
import { discoverExamplesInZip, type DiscoveredExample } from '@/src/utils/exampleZip';
import type { ExampleRepositoryGet, ExampleList, ExampleVersionList } from 'types/generated';

const DIR_OK = /^[a-zA-Z0-9._-]+$/;

interface UploadRow extends DiscoveredExample {
  status: 'pending' | 'uploading' | 'ok' | 'error';
  message?: string;
}

export default function ExampleRepositoryDetailPage() {
  const repositoryId = useParams().repositoryId as string;
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [repo, setRepo] = useState<ExampleRepositoryGet | null>(null);
  const [examples, setExamples] = useState<ExampleList[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload dialog
  const [uploadOpen, setUploadOpen] = useState(false);
  const [rows, setRows] = useState<UploadRow[]>([]);
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  // Expanded example -> versions
  const [openExample, setOpenExample] = useState<string | null>(null);
  const [versions, setVersions] = useState<Record<string, ExampleVersionList[]>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rRes, eRes] = await Promise.all([
        apiFetch(`${API_BASE_URL}/example-repositories/${repositoryId}`),
        apiFetch(`${API_BASE_URL}/examples?repository_id=${repositoryId}&limit=500`),
      ]);
      if (!rRes.ok) throw new Error('Failed to load repository');
      setRepo(await rRes.json());
      if (eRes.ok) setExamples(await eRes.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    load();
  }, [authLoading, isAuthenticated, canManage, load]);

  const uploadable = repo?.source_type === 'minio' || repo?.source_type === 's3';

  async function onPickZip(file: File | undefined) {
    if (!file) return;
    setParsing(true);
    setParseError(null);
    setRows([]);
    try {
      const discovered = await discoverExamplesInZip(file);
      setRows(discovered.map((d) => ({ ...d, status: 'pending' })));
    } catch (e) {
      setParseError(e instanceof Error ? e.message : 'Could not read the zip');
    } finally {
      setParsing(false);
    }
  }

  async function runUpload() {
    setUploading(true);
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, status: 'uploading', message: undefined } : r)));
      try {
        const res = await apiFetch(`${API_BASE_URL}/examples/upload`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ repository_id: repositoryId, directory: row.directory, files: row.files }),
        });
        if (!res.ok) throw new Error((await res.text()) || `Upload failed (${res.status})`);
        const v = await res.json();
        setRows((rs) =>
          rs.map((r, idx) => (idx === i ? { ...r, status: 'ok', message: `v${v.version_tag ?? ''}` } : r)),
        );
      } catch (e) {
        setRows((rs) =>
          rs.map((r, idx) =>
            idx === i ? { ...r, status: 'error', message: e instanceof Error ? e.message : 'Upload failed' } : r,
          ),
        );
      }
    }
    setUploading(false);
    await load();
  }

  function closeUpload() {
    setUploadOpen(false);
    setRows([]);
    setParseError(null);
  }

  async function toggleExample(exampleId: string) {
    if (openExample === exampleId) {
      setOpenExample(null);
      return;
    }
    setOpenExample(exampleId);
    if (!versions[exampleId]) {
      const res = await apiFetch(`${API_BASE_URL}/examples/${exampleId}/versions?limit=100`);
      if (res.ok) {
        const data = await res.json();
        setVersions((v) => ({ ...v, [exampleId]: data }));
      }
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="You do not have access to example management." backLink="/examples" backText="Back to Examples" />
      </AuthenticatedLayout>
    );
  }

  const dirsValid = rows.length > 0 && rows.every((r) => DIR_OK.test(r.directory));
  const allDone = rows.length > 0 && rows.every((r) => r.status === 'ok' || r.status === 'error');

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <div>
          <Link href="/examples" className="text-sm text-blue-600 hover:underline">
            ← Examples
          </Link>
          <div className="mt-2 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{repo?.name || 'Repository'}</h1>
              {repo && (
                <p className="mt-1 text-sm text-gray-500 font-mono">
                  {repo.source_type} · {repo.source_url}
                </p>
              )}
            </div>
            {uploadable && (
              <button
                onClick={() => setUploadOpen(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
              >
                Upload examples
              </button>
            )}
          </div>
        </div>

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

        <h2 className="text-xl font-semibold text-gray-900">
          Examples {!loading && <span className="text-gray-400 font-normal">({examples.length})</span>}
        </h2>

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : examples.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
            No examples yet.{uploadable ? ' Upload a zip containing one or more examples (each with a meta.yaml).' : ''}
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg divide-y">
            {examples.map((ex) => (
              <div key={ex.id}>
                <button
                  onClick={() => toggleExample(ex.id)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">{ex.title || ex.directory}</div>
                    <div className="text-xs text-gray-400 font-mono truncate">{ex.identifier}</div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {(ex.tags || []).slice(0, 3).map((t) => (
                      <span key={t} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">{t}</span>
                    ))}
                    <span className="text-gray-400 text-xs">{openExample === ex.id ? '▾' : '▸'}</span>
                  </div>
                </button>
                {openExample === ex.id && (
                  <div className="px-4 pb-3 bg-gray-50/50">
                    {!versions[ex.id] ? (
                      <div className="text-xs text-gray-400 py-2">Loading versions…</div>
                    ) : versions[ex.id].length === 0 ? (
                      <div className="text-xs text-gray-400 py-2">No versions.</div>
                    ) : (
                      <table className="w-full text-sm">
                        <tbody>
                          {versions[ex.id].map((v) => (
                            <tr key={v.id} className="border-t border-gray-200">
                              <td className="py-1.5 pr-4 font-mono text-xs text-gray-700">v{v.version_tag}</td>
                              <td className="py-1.5 pr-4 text-gray-500">{v.title || '—'}</td>
                              <td className="py-1.5 text-right text-xs text-gray-400">
                                {v.created_at ? new Date(v.created_at).toLocaleDateString() : ''}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload dialog */}
      {uploadOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4 max-h-[85vh] flex flex-col">
            <div className="p-6 space-y-4 overflow-y-auto">
              <h2 className="text-lg font-semibold text-gray-900">Upload examples</h2>
              <p className="text-sm text-gray-600">
                Choose a .zip containing a single example (a root <code className="font-mono">meta.yaml</code>) or
                several examples (each in its own folder with a <code className="font-mono">meta.yaml</code>).
              </p>

              <input
                type="file"
                accept=".zip,application/zip"
                onChange={(e) => onPickZip(e.target.files?.[0])}
                className="block w-full text-sm text-gray-600 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 file:text-sm file:font-medium hover:file:bg-blue-100"
              />

              {parsing && <div className="text-sm text-gray-500">Reading zip…</div>}
              {parseError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{parseError}</div>
              )}

              {rows.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-medium text-gray-500">
                    Discovered {rows.length} example{rows.length > 1 ? 's' : ''}
                  </div>
                  {rows.map((r, i) => (
                    <div key={i} className="flex items-center gap-3 border border-gray-200 rounded-lg px-3 py-2">
                      <input
                        value={r.directory}
                        disabled={uploading || r.status === 'ok'}
                        onChange={(e) =>
                          setRows((rs) => rs.map((x, idx) => (idx === i ? { ...x, directory: e.target.value } : x)))
                        }
                        className={`flex-1 px-2 py-1 border rounded text-sm font-mono ${
                          DIR_OK.test(r.directory) ? 'border-gray-300' : 'border-red-400'
                        }`}
                      />
                      <span className="text-xs text-gray-400 shrink-0">{r.fileCount} files</span>
                      <span
                        className={`text-xs shrink-0 w-40 truncate text-right ${
                          r.status === 'ok'
                            ? 'text-green-600'
                            : r.status === 'error'
                              ? 'text-red-600'
                              : r.status === 'uploading'
                                ? 'text-amber-600'
                                : 'text-gray-400'
                        }`}
                        title={r.message}
                      >
                        {r.status === 'pending'
                          ? 'ready'
                          : r.status === 'uploading'
                            ? 'uploading…'
                            : r.status === 'ok'
                              ? `uploaded ${r.message ?? ''}`
                              : r.message}
                      </span>
                    </div>
                  ))}
                  {!dirsValid && (
                    <p className="text-xs text-red-600">
                      Directory names may only contain letters, numbers, dots, dashes and underscores.
                    </p>
                  )}
                </div>
              )}
            </div>
            <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2 border-t border-gray-100">
              <button onClick={closeUpload} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">
                {allDone ? 'Close' : 'Cancel'}
              </button>
              <button
                onClick={runUpload}
                disabled={uploading || rows.length === 0 || !dirsValid || allDone}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {uploading ? 'Uploading…' : `Upload ${rows.length || ''}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </AuthenticatedLayout>
  );
}
