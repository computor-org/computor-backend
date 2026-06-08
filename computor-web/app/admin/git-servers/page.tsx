'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { apiFetch, API_BASE_URL } from '@/src/utils/apiClient';
import { useAuth } from '@/src/contexts/AuthContext';
import { usePermissions } from '@/src/hooks/usePermissions';
import AuthenticatedLayout from '@/src/components/AuthenticatedLayout';
import Breadcrumbs from '@/src/components/Breadcrumbs';
import type { GitServerGet } from '@/src/generated/types/common';

export default function GitServersPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { isAdmin, isOrganizationManager } = usePermissions();
  const canManage = isAdmin || isOrganizationManager;

  const [servers, setServers] = useState<GitServerGet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        <Breadcrumbs items={[{ label: 'Git Servers' }]} />
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Git Servers</h1>
            <p className="mt-2 text-gray-600">
              The registry of git instances courses can bind to. Managed instances hold a service token used for
              babysat student-repo provisioning.
            </p>
          </div>
          <Link href="/admin/git-servers/create" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            Register Server
          </Link>
        </div>

        {error && <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">{error}</div>}

        {loading ? (
          <div className="text-gray-500">Loading…</div>
        ) : servers.length === 0 ? (
          <div className="text-gray-500 border border-dashed border-gray-300 rounded-lg p-8 text-center">
            No git servers registered yet — register one (e.g. your Forgejo) to enable babysat provisioning.
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg divide-y">
            {servers.map((s) => (
              <Link key={s.id} href={`/admin/git-servers/${s.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-gray-900 truncate">{s.name || s.base_url}</div>
                  <div className="text-xs text-gray-500">{s.type} · {s.base_url}</div>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  {s.managed && <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-700 rounded">managed</span>}
                  <span className={`px-2 py-0.5 text-xs font-medium rounded ${s.has_token ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'}`}>
                    {s.has_token ? 'token set' : 'no token'}
                  </span>
                  <span className="text-gray-300">›</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AuthenticatedLayout>
  );
}
