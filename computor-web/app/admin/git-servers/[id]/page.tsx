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
import type { GitServerGet } from '@/src/generated/types/common';

export default function GitServerDetailPage() {
  const serverId = useParams().id as string;
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [server, setServer] = useState<GitServerGet | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch(`${API_BASE_URL}/git-servers/${serverId}`);
      if (!res.ok) throw new Error('Failed to load git server');
      setServer(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  }, [serverId]);

  useEffect(() => {
    if (authLoading || !isAuthenticated || !canManage) return;
    load();
  }, [authLoading, isAuthenticated, canManage, load]);

  async function remove() {
    if (!confirm('Remove this git server from the registry?')) return;
    const res = await apiFetch(`${API_BASE_URL}/git-servers/${serverId}`, { method: 'DELETE' });
    if (res.ok || res.status === 204) router.push('/admin/git-servers');
    else setError((await res.text()) || 'Delete failed');
  }

  if (!authLoading && isAuthenticated && !canManage) {
    return (
      <AuthenticatedLayout>
        <NotFound title="Not available" message="Admin or organization-manager access is required." backLink="/admin/git-servers" backText="Back" />
      </AuthenticatedLayout>
    );
  }

  return (
    <AuthenticatedLayout>
      <div className="p-6 space-y-6">
        <Breadcrumbs items={[{ label: 'Git Servers', href: '/admin/git-servers' }, { label: server?.name || server?.base_url || 'Git Server' }]} />

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : server ? (
          <>
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">{server.name || server.base_url}</h1>
                <p className="mt-1 text-sm text-gray-500 font-mono">{server.type} · {server.base_url}</p>
              </div>
              <div className="flex items-center gap-2">
                <Link href={`/admin/git-servers/${server.id}/edit`} className="px-3 py-2 text-sm font-medium text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50">
                  Edit
                </Link>
                <button onClick={remove} className="px-3 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50">
                  Delete
                </button>
              </div>
            </div>

            <div className="bg-white border border-gray-200 rounded-lg p-5 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Managed</dt>
                <dd className="text-gray-900">{server.managed ? 'Yes — Computor operates it' : 'No (external)'}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Service token</dt>
                <dd className="text-gray-900">{server.has_token ? 'Set (encrypted)' : 'None'}</dd>
              </div>
              {server.created_at && (
                <div>
                  <dt className="text-gray-500">Registered</dt>
                  <dd className="text-gray-900">{new Date(server.created_at).toLocaleString()}</dd>
                </div>
              )}
            </div>

            {server.managed && (
              <p className="text-xs text-gray-400">
                Managed Forgejo instances are auto-registered at startup. Removing one is blocked while any course binding still references it.
              </p>
            )}
          </>
        ) : null}
      </div>
    </AuthenticatedLayout>
  );
}
