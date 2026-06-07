'use client';

import { useCallback, useEffect, useState } from 'react';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import type { GitServerGet } from '@/src/generated/types/common';

const inputCls =
  'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';

type GitServerType = 'forgejo' | 'gitlab';

interface CreateState {
  open: boolean;
  saving: boolean;
  error: string | null;
  type: GitServerType;
  base_url: string;
  name: string;
  managed: boolean;
  token: string;
}

const emptyCreate: CreateState = {
  open: false,
  saving: false,
  error: null,
  type: 'forgejo',
  base_url: '',
  name: '',
  managed: true,
  token: '',
};

export default function GitServersPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [servers, setServers] = useState<GitServerGet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [create, setCreate] = useState<CreateState>(emptyCreate);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`${API_BASE_URL}/git-servers`);
      if (!res.ok) throw new Error('Failed to load git servers');
      setServers(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading || !isAuthenticated) return;
    if (!canManage) {
      setLoading(false);
      return;
    }
    load();
  }, [authLoading, isAuthenticated, canManage, load]);

  async function handleCreate() {
    setCreate((c) => ({ ...c, saving: true, error: null }));
    try {
      const res = await apiFetch(`${API_BASE_URL}/git-servers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: create.type,
          base_url: create.base_url.trim(),
          name: create.name.trim() || null,
          managed: create.managed,
          token: create.token.trim() || null,
        }),
      });
      if (!res.ok) throw new Error((await res.text()) || `Create failed (${res.status})`);
      setCreate(emptyCreate);
      await load();
    } catch (e) {
      setCreate((c) => ({ ...c, saving: false, error: e instanceof Error ? e.message : 'Create failed' }));
    }
  }

  async function handleDelete(server: GitServerGet) {
    if (!confirm(`Remove git server "${server.name || server.base_url}"?`)) return;
    try {
      const res = await apiFetch(`${API_BASE_URL}/git-servers/${server.id}`, { method: 'DELETE' });
      if (!res.ok && res.status !== 204) throw new Error((await res.text()) || `Delete failed (${res.status})`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed');
    }
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <div className="p-6">
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
            Admin or organization-manager access is required to manage git servers.
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Git Servers</h1>
            <p className="mt-2 text-gray-600">
              The registry of git instances courses can bind to. Managed instances hold a service token used for
              babysat student-repo provisioning.
            </p>
          </div>
          <button
            onClick={() => setCreate({ ...emptyCreate, open: true })}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
          >
            Register Server
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>
        )}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : servers.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
            No git servers registered yet — register one (e.g. your Forgejo) to enable babysat provisioning.
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg divide-y">
            {servers.map((s) => (
              <div key={s.id} className="flex items-center justify-between px-4 py-3">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-gray-900 truncate">{s.name || s.base_url}</div>
                  <div className="text-xs text-gray-500">
                    {s.type} · {s.base_url}
                  </div>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  {s.managed && (
                    <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded">managed</span>
                  )}
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded ${
                      s.has_token ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {s.has_token ? 'token set' : 'no token'}
                  </span>
                  <button onClick={() => handleDelete(s)} className="text-sm text-red-600 hover:underline">
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {create.open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="p-6 space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Register Git Server</h2>
              {create.error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{create.error}</div>
              )}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Type</label>
                <select
                  value={create.type}
                  onChange={(e) => setCreate((c) => ({ ...c, type: e.target.value as GitServerType }))}
                  className={inputCls}
                >
                  <option value="forgejo">forgejo</option>
                  <option value="gitlab">gitlab</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Base URL <span className="text-red-500">*</span>
                </label>
                <input
                  value={create.base_url}
                  onChange={(e) => setCreate((c) => ({ ...c, base_url: e.target.value }))}
                  placeholder="http://localhost:3030"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Name</label>
                <input
                  value={create.name}
                  onChange={(e) => setCreate((c) => ({ ...c, name: e.target.value }))}
                  placeholder="Our Forgejo"
                  className={inputCls}
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={create.managed}
                  onChange={(e) => setCreate((c) => ({ ...c, managed: e.target.checked }))}
                />
                Managed (Computor operates it and holds a service token)
              </label>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Service token {create.managed && <span className="text-gray-400">(needed for babysat provisioning)</span>}
                </label>
                <input
                  type="password"
                  value={create.token}
                  onChange={(e) => setCreate((c) => ({ ...c, token: e.target.value }))}
                  placeholder="stored encrypted, never returned"
                  className={inputCls}
                />
              </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 rounded-b-xl flex justify-end gap-2">
              <button
                onClick={() => setCreate(emptyCreate)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={create.saving || !create.base_url.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {create.saving ? 'Saving…' : 'Register'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AuthenticatedLayout>
  );
}
